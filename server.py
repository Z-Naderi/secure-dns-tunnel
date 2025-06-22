# server/server.py

from dnslib.server import DNSServer, BaseResolver
from dnslib import RR, QTYPE, A
import base64
from crypto_module import AESCipher
from collections import defaultdict
import socket


SHARED_KEY = b"0123456789ABCDEF0123456789ABCDEF"
DOMAIN = "tunnel.example.com"
RESPONSE_IP = "1.2.3.4"  

cipher = AESCipher(SHARED_KEY)
received_chunks = {}

class DNSAgentResolver(BaseResolver):
    def resolve(self, request, handler):
        qname = str(request.q.qname).rstrip('.')
        labels = qname.split('.')

        
        if not qname.endswith(DOMAIN):
            return request.reply()

        try:
            seq_label = labels[0]
            if not seq_label.startswith("seq"):
                return request.reply()

            seq_num = int(seq_label[3:])
            encoded_data = ''.join(labels[1:-len(DOMAIN.split('.'))])
            padded = encoded_data.upper() + '=' * (-len(encoded_data) % 8)
            full_packet = base64.b32decode(padded)

            nonce = full_packet[:16]
            tag = full_packet[16:32]
            ciphertext = full_packet[32:]

            plaintext = cipher.decrypt(ciphertext, nonce, tag)

            if seq_num not in received_chunks:
                received_chunks[seq_num] = plaintext
                print(f"[✓] Received chunk {seq_num}: {plaintext}")
            else:
                print(f"[=] Duplicate chunk {seq_num} ignored.")

        except Exception as e:
            print(f"[!] Error parsing query: {e}")

        reply = request.reply()
        reply.add_answer(RR(rname=request.q.qname, rtype=QTYPE.A, rclass=1, ttl=60, rdata=A(RESPONSE_IP)))
        return reply

def start_dns_server():
    resolver = DNSAgentResolver()
    server = DNSServer(resolver, port=5353, address="127.0.0.1", tcp=False)
    server.start_thread()

    print(f" DNS Tunnel Server running on port 53...\nListening for data on domain: {DOMAIN}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n Shutting down... rebuilding message:")
        message = b''.join([received_chunks[i] for i in sorted(received_chunks)])
        print(f" Reconstructed message:\n{message.decode(errors='ignore')}")

if __name__ == "__main__":
    start_dns_server()
