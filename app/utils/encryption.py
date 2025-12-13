from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
import os
from .logging import get_logger

log = get_logger(__file__)

def get_key():
    load_dotenv()
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        raise ValueError("No Encryption Key Specified")
    return key.encode('utf-8')

def encrypt_data(plain_text):
    if not plain_text:
        raise ValueError("Cannot encrypt nothing")
    try:
        fernet = Fernet(get_key())
        return fernet.encrypt(plain_text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        log.error(f"Encryption Failed: {e}")
        raise RuntimeError("Encryption Error") from e

def decrypt_data(cipher_text):
    if not cipher_text:
        raise ValueError("Cannot decrypt nothing")
    try:
        fernet = Fernet(get_key())
        return fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        log.warning('Invalid decryption token')
        raise ValueError('Invalid or corrupted Cipher Text')
    except Exception as e:
        log.error(f"Decryption Failed: {e}")
        raise RuntimeError("Decryption Error") from e

