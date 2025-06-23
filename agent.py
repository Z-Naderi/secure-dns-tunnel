# agent/agent.py

import base64
import dns.resolver
import time
import dns.message
import dns.query
from crypto_module import AESCipher

SHARED_KEY = b"0123456789ABCDEF0123456789ABCDEF"  
CHUNK_SIZE = 30  
DOMAIN = "tunnel.example.com"  
MAX_RETRIES = 3 


cipher = AESCipher(SHARED_KEY)

def split_data(data: bytes, size: int):
    return [data[i:i+size] for i in range(0, len(data), size)]

def build_label(seq: int, encrypted: bytes) -> str:
    encoded = base64.b32encode(encrypted).decode().strip('=').lower()
    
    
    labels = [encoded[i:i+50] for i in range(0, len(encoded), 50)]
    return f"seq{seq}." + ".".join(labels) + f".{DOMAIN}"


def send_dns_query(label: str) -> bool:
    try:
        query = dns.message.make_query(label, dns.rdatatype.A)
        response = dns.query.udp(query, '127.0.0.1', port=5353, timeout=2)

        
        for answer in response.answer:
            if answer.rdtype == dns.rdatatype.A:
                return True

        return False  

    except Exception as e:
        print(f"❌ DNS error for {label}: {e}")
        return False



def send_chunk_with_ack(chunk: bytes, seq: int):
    
    encrypted = cipher.encrypt(chunk)
    packet = encrypted['nonce'] + encrypted['tag'] + encrypted['ciphertext']
    label = build_label(seq, packet)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"🔹 Sending chunk {seq}, try {attempt}...")
        if send_dns_query(label):
            print(f"✅ ACK received for chunk {seq}")
            return True
        else:
            print(f"⚠️  No ACK for chunk {seq}, retrying...")
        time.sleep(1)

    print(f"🚨 Failed to send chunk {seq} after {MAX_RETRIES} attempts.")
    return False

def main():
    message = input("Enter your message: ").encode()
    chunks = split_data(message, CHUNK_SIZE)

    for seq, chunk in enumerate(chunks):
        success = send_chunk_with_ack(chunk, seq)
        if not success:
            print("Aborting transmission due to repeated failure.")
            break  

if __name__ == "__main__":
    main()
