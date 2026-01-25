# utils.py
from cryptography.fernet import Fernet
import hashlib

EMAIL_KEY = b'z8jU7Ih0F3z9Z0H2M7qfG5kA1L0xV1yN5B6pD8tR9Q0='

fernet = Fernet(EMAIL_KEY)

def encrypt_email(email: str) -> str:
    return fernet.encrypt(email.encode()).decode()

def decrypt_email(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()

def hash_email(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()