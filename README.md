# Secure DNS Tunneling with Symmetric Encryption

This project implements a secure and covert communication system where a client (Agent) sends encrypted data via DNS queries to a server. It demonstrates the use of symmetric cryptography (specifically AES-256 in GCM mode) to protect data during transit, effectively creating a DNS tunnel.

## 🌟 Features

**Secure Communication**: Data is encrypted using AES-256 GCM before being sent over DNS, ensuring confidentiality and integrity.
**Covert Channel**: Utilizes DNS queries as a hidden communication channel, making it ideal for bypassing network restrictions where only DNS traffic is allowed.
**Reliable Transmission**: Implements an acknowledgment mechanism so the Agent knows if the server received the data. Retries for chunks are also implemented to ensure data delivery.
**Data Integrity**: AES-GCM provides authentication, verifying that the received data has not been tampered with.
**Chunking and Reassembly**: Large messages are split into smaller chunks, sent individually, and then reassembled at the server.
**Sequence Numbering**: Each chunk includes a sequence number to ensure correct order and message validity.

## 🚀 How it Works

The system operates with three main components:

1.  **Agent (Client)**: Acts as the data sender. It encrypts the data using a symmetric key (e.g., AES-256), encodes the encrypted chunks using Base32 or Base64 to fit into DNS labels, and sends them as part of DNS A queries. It also implements acknowledgment messages.
2.  **Server (Receiver)**: A custom DNS server that listens for incoming DNS queries. It extracts data from the query subdomain, decodes and decrypts each chunk using the symmetric key, then reconstructs the original message.
3.  **Crypto Module (Shared)**: This module is shared between the Server and Agent. It uses AES (CBC or GCM) for encryption and decryption, manages padding, IV/nonce generation, and cryptographic integrity. The key is manually configured and pre-shared.

### Communication Flow

1.  The `Agent` reads the data (e.g., a message or file).
2.  The data is divided into smaller chunks.
3.  Each chunk is:
    * Encrypted with AES.
    * Encoded with Base32.
    * Sent as a DNS query.
4.  The `Server` receives the DNS query.
5.  It extracts the subdomain, decodes and decrypts it.
6.  The `Server` reconstructs the original data.
7.  Upon successful reception and decryption, the Server sends a DNS A record reply (`1.2.3.4`) as an acknowledgment.
8.  The Agent waits for the acknowledgment. If not received within a timeout, it retries sending the chunk up to `MAX_RETRIES` (3 times).

## 🛠️ Setup and Installation

### Prerequisites

* Python 3.x
* `dnspython` library
* `dnslib` library
* `pycryptodome` library

You can install the required Python libraries using pip:

```bash
pip install dnspython dnslib pycryptodome
```

### Project Structure

```
.
├── agent.py
├── server.py
├── crypto_module.py
└── README.md
```

### Configuration

  * `SHARED_KEY`: A 32-byte (256-bit) AES key. This key must be identical in `agent.py`, `server.py`, and `crypto_module.py`.
    ```python
    SHARED_KEY = b"0123456789ABCDEF0123456789ABCDEF" # Example Key - **DO NOT USE IN PRODUCTION**
    ```
  * `DOMAIN`: The domain used for tunneling (e.g., `tunnel.example.com`). This must be consistent between `agent.py` and `server.py`.
  * `CHUNK_SIZE`: The maximum size of data (in bytes) to be sent in each chunk. (Currently set to 30 bytes in `agent.py`).
  * `MAX_RETRIES`: The number of times the agent will attempt to send a chunk if an acknowledgment is not received. (Currently set to 3 in `agent.py`).

## 🚀 Usage

### 1\. Start the DNS Tunnel Server

Open a terminal and run the `server.py` script. The server will start listening for DNS queries on `127.0.0.1:5353`.

```bash
python server.py
```
You should see output similar to:


🔒 DNS Tunnel Server running on port 53...
Listening for data on domain: tunnel.example.com


### 2\. Run the Agent (Client)

Open *another* terminal and run the `agent.py` script. It will prompt you to enter a message.

```bash
python agent.py
```

Enter your message and press Enter. The agent will then start sending the message in chunks via DNS queries.

```
Enter your message: Hello, this is a secret message sent over DNS.
🔹 Sending chunk 0, try 1...
✅ ACK received for chunk 0
🔹 Sending chunk 1, try 1...
✅ ACK received for chunk 1
...
```

### 3\. Observe Data Reception on the Server

As the agent sends chunks, the server terminal will display the received and decrypted chunks:

```
✅ Received chunk 0: b'Hello, this is a secret mes'
✅ Received chunk 1: b'sage sent over DNS.'
...
```

### 4\. Reconstruct the Message (Server Side)

To see the reconstructed message, stop the server by pressing `Ctrl+C`. The server will then attempt to reassemble all received chunks and print the full message. It will also indicate if any chunks were missing.

```
⚠️  Shutting down... rebuilding message:
 ✅ Reconstructed message:
    Hello, this is a secret message sent over DNS.
✅ Received chunks: [0, 1]
✅ All chunks received successfully.
```

## ⚠️ Important Notes

  * **Security**: The `SHARED_KEY` is hardcoded in this example. In a real-world scenario, this key should be securely generated, managed, and exchanged (e.g., using a key exchange protocol).
  * **DNS Resolver**: The `agent.py` script is configured to send DNS queries to `127.0.0.1:5353`. If you are running the server on a different machine or port, you will need to adjust this accordingly.
  * **Packet Size Limitations**: DNS query labels have size limitations (63 characters per label, 255 characters total for a QNAME). The `CHUNK_SIZE` and Base32 encoding are designed to fit within these limits. Larger chunks would require more complex label splitting.
  * **Error Handling**: Basic error handling for DNS queries is implemented (retries). More robust error handling and potentially a more sophisticated acknowledgment mechanism might be needed for production systems.
  * **Stealth**: While this method uses DNS for tunneling, sophisticated network monitoring tools might still detect unusual DNS traffic patterns (e.g., frequent queries to a specific domain with large, unusual subdomains) and flag them as suspicious.

