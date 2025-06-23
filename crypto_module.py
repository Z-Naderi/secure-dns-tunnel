# crypto/crypto_module.py

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class AESCipher:
    def __init__(self, key: bytes):
        """
        Constructor to initialize the AES cipher with a given key.
        The key must be exactly 32 bytes long for AES-256 encryption.
        """
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes (256 bits) for AES-256.")
        self.key = key

    def encrypt(self, plaintext: bytes):
        """
        Encrypts the plaintext using AES-256 in GCM (Galois/Counter Mode).
        Returns the encrypted ciphertext, nonce (used in encryption), and the authentication tag.
        """
        # Create a new AES cipher instance in GCM mode with the given key
        cipher = AES.new(self.key, AES.MODE_GCM)
        
        # Encrypt the plaintext and generate the authentication tag
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        
        # Return the encrypted data, the nonce, and the authentication tag
        return {
            'ciphertext': ciphertext,  # The encrypted message
            'nonce': cipher.nonce,     # The nonce used for encryption (important for GCM)
            'tag': tag                 # The authentication tag for verifying integrity
        }

    def decrypt(self, ciphertext: bytes, nonce: bytes, tag: bytes):
        """
        Decrypts the ciphertext using AES-256 GCM with the provided nonce and authentication tag.
        Verifies the integrity of the ciphertext using the tag.
        Returns the decrypted plaintext if valid, otherwise raises an error.
        """
        # Create a new AES cipher instance in GCM mode with the given key and nonce
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        # Decrypt the ciphertext and verify the tag to ensure data integrity
        return cipher.decrypt_and_verify(ciphertext, tag)
