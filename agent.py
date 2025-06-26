import base64
import dns.resolver
import time
from crypto_module import AESCipher
import hashlib

SHARED_KEY = b"0123456789ABCDEF0123456789ABCDEF"
#print("🔑 Key SHA256 hash:", hashlib.sha256(SHARED_KEY).hexdigest())
if len(SHARED_KEY) != 32:
    raise ValueError("🔐 SHARED_KEY must be exactly 32 bytes long for AES-256.")
CHUNK_SIZE = 50
DOMAIN = "tunnel.example.com"
TIMEOUT = 4

cipher = AESCipher(SHARED_KEY)

def split_data(data: bytes, size: int):
    return [data[i:i+size] for i in range(0, len(data), size)]

def build_label(seq: int, encrypted: bytes) -> str:
    encoded = base64.b32encode(encrypted).decode().strip('=')
    labels = [encoded[i:i+63] for i in range(0, len(encoded), 63)]
    return f"seq{seq}." + ".".join(labels) + f".{DOMAIN}"

def send_reset_signal():
    reset_label = f"seq-1.reset.{DOMAIN}"
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['127.0.0.1']
    resolver.port = 5354
    resolver.timeout = TIMEOUT
    resolver.lifetime = TIMEOUT

    print("🔹 Sending reset signal...")
    try:
        answers = resolver.resolve(reset_label, 'A', tcp=True)
        for answer in answers:
            if str(answer) == "1.2.0.0":
                print("✅ Server reset confirmed")
                return True
    except Exception as e:
        print(f"❌ Reset error: {e}")
    return False

def send_chunk(seq, chunk, base):
    encrypted = cipher.encrypt(chunk)
    packet = encrypted['nonce'] + encrypted['tag'] + encrypted['ciphertext']
    label = build_label(seq, packet)

    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['127.0.0.1']
    resolver.port = 5354
    resolver.timeout = TIMEOUT
    resolver.lifetime = TIMEOUT

    try:
        answers = resolver.resolve(label, 'A', tcp=True)
        for answer in answers:
            ack_ip = str(answer)
            parts = ack_ip.split('.')
            if parts[:2] == ['1', '2']:
                ack_seq = int(parts[2]) * 256 + int(parts[3])
                if ack_seq < base:
                    print(f"⚠️ Ignoring stale ACK for already dropped chunk {ack_seq}")
                    time.sleep(0.1)
                    continue
                return ack_seq
    except Exception as e:
        print(f"❌ Error sending chunk {seq}: {e}")
    return None

def main():
    if not send_reset_signal():
        print("🚨 Reset failed, aborting.")
        return

    message = input("Enter your message: ").encode()
    chunks = split_data(message, CHUNK_SIZE)
    total_chunks = len(chunks)
    print(f"📆 Total chunks: {total_chunks}")

    cwnd = 2
    ssthresh = 8
    base = 0
    next_seq = 0
    in_flight = {}
    last_ack = -1
    dup_ack_count = 0
    in_fast_recovery = False
    max_retransmit_per_chunk = 5
    retransmit_count = {i: 0 for i in range(total_chunks)}

    while base < total_chunks:
        # ارسال چانک‌ها
        while next_seq < base + cwnd and next_seq < total_chunks:
            print(f"📤 Sending chunk {next_seq}")
            in_flight[next_seq] = {
                'data': chunks[next_seq],
                'time': time.time()
            }
            next_seq += 1

        # بررسی timeout
        now = time.time()
        to_retransmit = []
        for seq in list(in_flight.keys()):
            if now - in_flight[seq]['time'] > TIMEOUT:
                to_retransmit.append(seq)

        if to_retransmit:
            print(f"⏱ Timeout for chunks: {to_retransmit}")
            for seq in to_retransmit:
                retransmit_count[seq] += 1
                if retransmit_count[seq] > max_retransmit_per_chunk:
                    print(f"⛔ Chunk {seq} dropped after {max_retransmit_per_chunk} timeouts.")
                    in_flight.pop(seq, None)
                    if base == seq:
                        base = seq + 1
                        next_seq = base
                        dup_ack_count = 0
                        in_fast_recovery = False
                    continue
                else:
                    in_flight[seq]['time'] = time.time()  # Refresh time

            ssthresh = max(cwnd // 2, 1)
            cwnd = 1
            next_seq = base
            dup_ack_count = 0
            in_fast_recovery = False
            continue

        ack_seq = send_chunk(base, chunks[base], base)

        if ack_seq is None:
            time.sleep(1)
            continue

        if ack_seq > base:
            print(f"✅ ACK received for seq {ack_seq - 1}")
            for seq in range(base, ack_seq):
                in_flight.pop(seq, None)
            base = ack_seq
            dup_ack_count = 0
            last_ack = ack_seq
            if in_fast_recovery:
                print(f"✅ Exiting Fast Recovery: cwnd = {ssthresh}")
                cwnd = ssthresh
                in_fast_recovery = False
            elif cwnd < ssthresh:
                cwnd *= 2
                print(f"🚀 Slow Start → cwnd = {cwnd}")
            else:
                cwnd += 1
                print(f"📈 Congestion Avoidance → cwnd = {cwnd}")
        elif ack_seq == last_ack:
            dup_ack_count += 1
            print(f"🔁 Duplicate ACK for {ack_seq} ({dup_ack_count})")
            if dup_ack_count >= 15: 
                print(f"⛔ Too many duplicate ACKs for chunk {ack_seq}, skipping it.")
                retransmit_count[ack_seq] += 1
                if retransmit_count[ack_seq] > max_retransmit_per_chunk:
                    print(f"⛔ Chunk {ack_seq} dropped after {max_retransmit_per_chunk} retransmits.")
                    in_flight.pop(ack_seq, None)
                    if base == ack_seq:
                        base = ack_seq + 1
                        next_seq = base
                        last_ack = base  #  Very important to avoid loop
                        dup_ack_count = 0
                        in_fast_recovery = False
                        continue

            if dup_ack_count == 3 and not in_fast_recovery:
                retransmit_count[ack_seq] += 1
                if retransmit_count[ack_seq] > max_retransmit_per_chunk:
                    print(f"⛔ Chunk {ack_seq} dropped after {max_retransmit_per_chunk} retransmits.")
                    in_flight.pop(ack_seq, None)
                    base = ack_seq + 1
                    next_seq = base
                    dup_ack_count = 0
                    in_fast_recovery = False
                    continue
                print(f"🚀 Fast Retransmit: Resending chunk {ack_seq}")
                dup_ack_count = 0
                if ack_seq in chunks:
                    in_flight[ack_seq] = {
                        'data': chunks[ack_seq],
                        'time': time.time()
                    }
                    ssthresh = max(cwnd // 2, 1)
                    cwnd = ssthresh + 3
                    in_fast_recovery = True
        else:
            dup_ack_count = 1
            last_ack = ack_seq

        time.sleep(0.1)

    print("✅ All chunks sent and acknowledged.")

if __name__ == "__main__":
    main()
