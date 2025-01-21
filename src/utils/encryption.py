from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from src.config import get_settings
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

settings = get_settings()

def get_encryption_key() -> bytes:
    """
    Generate a Fernet key using PBKDF2 with environment variables
    """
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=settings.encryption_salt.encode(),
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(settings.encryption_key.encode()))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate encryption key. Please check encryption settings."
        )

# Initialize Fernet cipher with the derived key
cipher_suite = Fernet(get_encryption_key())

def encrypt_password(password: str) -> str:
    """
    Encrypt a password using Fernet (symmetric encryption)
    """
    try:
        encrypted_data = cipher_suite.encrypt(password.encode())
        return encrypted_data.decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encrypt password"
        )

def decrypt_password(encrypted_password: str) -> str:
    """
    Decrypt a password that was encrypted using Fernet
    """
    try:
        decrypted_data = cipher_suite.decrypt(encrypted_password.encode())
        return decrypted_data.decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not decrypt password"
        ) 