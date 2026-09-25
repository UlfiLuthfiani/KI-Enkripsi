"""
crypto_core.py
Modul inti kriptografi untuk aplikasi "Surat untuk Masa Depan" (Kapsul Waktu Digital).

Menyediakan:
- Key derivation dari password (Argon2id / PBKDF2) dengan salt acak
- Enkripsi/dekripsi AES-256-GCM
- Enkripsi/dekripsi ChaCha20-Poly1305
- Enkripsi hibrida: session key AES dibungkus RSA-OAEP (fitur pengayaan)

Semua fungsi mengembalikan/menerima bytes mentah. Konversi ke Base64/hex
dilakukan di layer UI (app.py) agar modul ini tetap murni logika kripto.
"""

import os
import base64
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidTag
from argon2.low_level import hash_secret_raw, Type

# ---------------------------------------------------------------------------
# Konstanta
# ---------------------------------------------------------------------------
SALT_SIZE = 16          # bytes, untuk key derivation
NONCE_SIZE = 12          # bytes, standar untuk AES-GCM & ChaCha20-Poly1305
KEY_SIZE = 32          # bytes -> 256 bit

# Parameter Argon2id (disesuaikan agar cukup aman tapi tidak terlalu lambat
# untuk demo; boleh dinaikkan untuk penggunaan produksi nyata)
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536   # 64 MB
ARGON2_PARALLELISM = 4


class DecryptionError(Exception):
    """Dilempar ketika dekripsi gagal: password salah atau cipherteks/tag rusak."""
    pass


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------
def derive_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """
    Menurunkan kunci 256-bit dari password menggunakan Argon2id.
    Jika salt tidak diberikan, salt acak baru akan dibangkitkan.

    Returns:
        (key, salt) - keduanya bytes
    """
    if salt is None:
        salt = os.urandom(SALT_SIZE)

    key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=KEY_SIZE,
        type=Type.ID,  # Argon2id
    )
    return key, salt


# ---------------------------------------------------------------------------
# AES-256-GCM
# ---------------------------------------------------------------------------
def encrypt_aes_gcm(plaintext: bytes, key: bytes, associated_data: bytes = b"") -> tuple[bytes, bytes]:
    """Mengenkripsi plaintext dengan AES-256-GCM. Return (ciphertext_with_tag, nonce)."""
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    return ciphertext, nonce


def decrypt_aes_gcm(ciphertext: bytes, key: bytes, nonce: bytes, associated_data: bytes = b"") -> bytes:
    """Mendekripsi ciphertext AES-256-GCM. Raise DecryptionError jika gagal."""
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, associated_data)
    except InvalidTag:
        raise DecryptionError("Password salah atau cipherteks telah diubah (verifikasi tag gagal).")


# ---------------------------------------------------------------------------
# ChaCha20-Poly1305
# ---------------------------------------------------------------------------
def encrypt_chacha20(plaintext: bytes, key: bytes, associated_data: bytes = b"") -> tuple[bytes, bytes]:
    """Mengenkripsi plaintext dengan ChaCha20-Poly1305. Return (ciphertext_with_tag, nonce)."""
    nonce = os.urandom(NONCE_SIZE)
    chacha = ChaCha20Poly1305(key)
    ciphertext = chacha.encrypt(nonce, plaintext, associated_data)
    return ciphertext, nonce


def decrypt_chacha20(ciphertext: bytes, key: bytes, nonce: bytes, associated_data: bytes = b"") -> bytes:
    """Mendekripsi ciphertext ChaCha20-Poly1305. Raise DecryptionError jika gagal."""
    chacha = ChaCha20Poly1305(key)
    try:
        return chacha.decrypt(nonce, ciphertext, associated_data)
    except InvalidTag:
        raise DecryptionError("Password salah atau cipherteks telah diubah (verifikasi tag gagal).")


# ---------------------------------------------------------------------------
# Enkripsi hibrida: RSA-OAEP membungkus session key AES (fitur pengayaan)
# ---------------------------------------------------------------------------
def generate_rsa_keypair(key_size: int = 2048):
    """Membangkitkan pasangan kunci RSA baru untuk 'penerima' kapsul."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    public_key = private_key.public_key()
    return private_key, public_key


def serialize_private_key(private_key, password: bytes | None = None) -> bytes:
    encryption = (
        serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )


def serialize_public_key(public_key) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_private_key(pem_bytes: bytes, password: bytes | None = None):
    return serialization.load_pem_private_key(pem_bytes, password=password)


def load_public_key(pem_bytes: bytes):
    return serialization.load_pem_public_key(pem_bytes)


def wrap_session_key(session_key: bytes, public_key) -> bytes:
    """Membungkus session key AES memakai RSA-OAEP dengan public key penerima."""
    return public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def unwrap_session_key(wrapped_key: bytes, private_key) -> bytes:
    """Membuka bungkus session key AES memakai RSA-OAEP dengan private key penerima."""
    try:
        return private_key.decrypt(
            wrapped_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except ValueError:
        raise DecryptionError("Gagal membuka session key: private key salah atau data rusak.")


# ---------------------------------------------------------------------------
# Util encoding
# ---------------------------------------------------------------------------
def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def from_b64(text: str) -> bytes:
    return base64.b64decode(text)


def to_hex(data: bytes) -> str:
    return data.hex()


def from_hex(text: str) -> bytes:
    return bytes.fromhex(text)
