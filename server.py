import base64
from dnslib.server import DNSServer, BaseResolver
from dnslib import RR, QTYPE, A
from crypto_module import AESCipher
import hashlib
from threading import Lock

SHARED_KEY = b"0123456789ABCDEF0123456789ABCDEF"
#print("🔑 Key SHA256 hash:", hashlib.sha256(SHARED_KEY).hexdigest())
if len(SHARED_KEY) != 32:
    raise ValueError("🔐 SHARED_KEY must be exactly 32 bytes long for AES-256.")
DOMAIN = "tunnel.example.com"

cipher = AESCipher(SHARED_KEY)
received_chunks = {}
expected_seq = 0  # This will track the next expected sequence number
seq_lock = Lock()

class DNSAgentResolver(BaseResolver):
    def resolve(self, request, handler):
        global expected_seq
        qname = str(request.q.qname).rstrip('.')
        labels = qname.split('.')
        reply = request.reply()

        if not qname.endswith(DOMAIN):
            return reply

        try:
            seq_label = labels[0]
            if not seq_label.startswith("seq"):
                return reply

            seq_num = int(seq_label[3:])


            # Simulate packet loss for chunk 5 (for testing)

            # Handle reset request explicitly
            if seq_num == -1:
                with seq_lock:
                    print(f"🔄 Before reset: expected_seq={expected_seq}, received_chunks={received_chunks}")
                    received_chunks.clear()
                    expected_seq = 0
                    print("🔄 Server state reset by client.")
                ack_ip = "1.2.0.0"
                reply.add_answer(RR(rname=request.q.qname, rtype=QTYPE.A, ttl=60, rdata=A(ack_ip)))
                return reply

            # Ignore chunks older than expected_seq
            with seq_lock:
                if seq_num < expected_seq:
                    print(f"⏭ Ignoring chunk {seq_num} as it is older than expected_seq={expected_seq}")
                    ack_ip = f"1.2.{expected_seq // 256}.{expected_seq % 256}"
                    reply.add_answer(RR(rname=request.q.qname, rtype=QTYPE.A, ttl=60, rdata=A(ack_ip)))
                    return reply

            # Base32 decoding and decrypting the message
            encoded_data = ''.join(labels[1:-len(DOMAIN.split('.'))])
            padded = encoded_data.upper() + '=' * (-len(encoded_data) % 8)

            try:
                full_packet = base64.b32decode(padded)
            except Exception as e:
                print(f"❗ Base32 decode error: {e}")
                return reply

            if len(full_packet) < 32:
                print(f"❗ Malformed packet from seq {seq_num} (length {len(full_packet)})")
                return reply

            nonce = full_packet[:16]
            tag = full_packet[16:32]
            ciphertext = full_packet[32:]

            try:
                plaintext = cipher.decrypt(ciphertext, nonce, tag)
            except Exception as e:
                print(f"❗ Decryption failed for seq {seq_num}: {e}")
                return reply

            # Store the chunk and update expected_seq
            with seq_lock:
                if seq_num not in received_chunks:
                    received_chunks[seq_num] = plaintext
                    print(f"✅ Stored chunk {seq_num}")
                    while expected_seq in received_chunks:
                        expected_seq += 1
                else:
                    print(f"🔁 Duplicate chunk {seq_num} ignored.")

            try:
                decoded_str = plaintext.decode("utf-8", errors="ignore")
                print(f"📦 Received {seq_num}: {decoded_str}")
            except:
                print(f"📦 Received {seq_num}: [binary data]")

            # Send the ACK for the next expected sequence
            ack_ip = f"1.2.{expected_seq // 256}.{expected_seq % 256}"
            reply.add_answer(RR(rname=request.q.qname, rtype=QTYPE.A, ttl=60, rdata=A(ack_ip)))

        except Exception as e:
            print(f"❗ Error: {e}")
            ack_ip = f"1.2.{expected_seq // 256}.{expected_seq % 256}"
            reply.add_answer(RR(rname=request.q.qname, rtype=QTYPE.A, ttl=60, rdata=A(ack_ip)))

        return reply

def start_dns_server():
    resolver = DNSAgentResolver()
    server = DNSServer(resolver, port=5354, address="127.0.0.1", tcp=True)
    server.start_thread()

    print(f"🔒 DNS Tunnel Server running on 127.0.0.1:5354 for domain {DOMAIN}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("⚠️ Shutting down...")
        if received_chunks:
            try:
                message = b''.join([received_chunks[i] for i in sorted(received_chunks.keys())])
                print(f"✅ Reconstructed message:\n    {message.decode('utf-8', errors='ignore')}")
                expected = max(received_chunks.keys()) + 1
                missing = set(range(expected)) - set(received_chunks.keys())
                print(f"✅ Received chunks: {sorted(received_chunks.keys())}")
                if missing:
                    print(f"⚠️ Missing chunks: {sorted(missing)}")
                else:
                    print("✅ All chunks received successfully.")
            except Exception as e:
                print(f"❗ Error while reconstructing message: {e}")
        else:
            print("⚠️ No chunks received. Nothing to reconstruct.")

if __name__ == "__main__":
    start_dns_server()