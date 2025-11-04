"""Simple password hashing using Argon2id.

Based on argon2-cffi documentation: https://argon2-cffi.readthedocs.io/en/stable/howto.html
"""

from argon2 import PasswordHasher

# Create a single instance
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password for secure storage.
    
    Args:
        password: Plaintext password to hash
        
    Returns:
        Hashed password string
    """
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored hash.
    
    Args:
        password: Plaintext password to verify
        password_hash: Stored hash from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        ph.verify(password_hash, password)
        return True
    except Exception:  # VerifyMismatchError or other exceptions
        return False