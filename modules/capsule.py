"""capsule.py - format kapsul v2.
Kunci akhir = HKDF(kunci_password || kunci_waktu). kunci_waktu = HMAC(TIMELOCK_SECRET, id|unlock_ts)
hanya bisa dihitung server, dan server menolak menghitungnya sebelum tanggal buka.
Mengubah unlock_timestamp di JSON -> kunci_waktu berbeda + AAD berbeda -> dekripsi gagal.
Mode hibrida: kunci sesi acak dibungkus RSA-OAEP menggantikan kunci_password."""
import os, json, hmac, hashlib, uuid
from datetime import datetime
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from . import crypto_core as cc, timelock as tl

VERSION = 2
ALGOS = {"AES-256-GCM": (cc.encrypt_aes_gcm, cc.decrypt_aes_gcm),
         "ChaCha20-Poly1305": (cc.encrypt_chacha20, cc.decrypt_chacha20)}


def _time_key(cid: str, ts: int) -> bytes:
    secret = os.environ.get("TIMELOCK_SECRET")
    if not secret:
        raise RuntimeError("TIMELOCK_SECRET belum diset. Salin .env.example menjadi .env")
    return hmac.new(secret.encode(), f"{cid}|{ts}".encode(), hashlib.sha256).digest()


def _final_key(base: bytes, cid: str, ts: int) -> bytes:
    return HKDF(hashes.SHA256(), cc.KEY_SIZE, salt=cid.encode(), info=b"kapsul-v2").derive(base + _time_key(cid, ts))


def _aad(c: dict) -> bytes:
    keys = ("version", "id", "algorithm", "unlock_timestamp", "is_file", "filename")
    return json.dumps({k: c[k] for k in keys}, sort_keys=True).encode()


def create_capsule(plaintext, password, unlock_datetime: datetime, algorithm="AES-256-GCM",
                   is_file=False, filename=None, recipient_public_key=None) -> dict:
    if algorithm not in ALGOS:
        raise ValueError(f"Algoritma tidak dikenal: {algorithm}")
    cid, ts = uuid.uuid4().hex, tl.make_unlock_timestamp(unlock_datetime)
    c = {"version": VERSION, "id": cid, "algorithm": algorithm, "unlock_timestamp": ts,
         "is_file": is_file, "filename": filename, "salt": "", "hybrid": None}
    if recipient_public_key is not None:
        base = os.urandom(cc.KEY_SIZE)
        c["hybrid"] = {"wrapped_session_key": cc.to_b64(cc.wrap_session_key(base, recipient_public_key))}
    else:
        base, salt = cc.derive_key(password)
        c["salt"] = cc.to_b64(salt)
    ct, nonce = ALGOS[algorithm][0](plaintext, _final_key(base, cid, ts), _aad(c))
    c["nonce"], c["ciphertext"] = cc.to_b64(nonce), cc.to_b64(ct)
    return c


def open_capsule(c: dict, password="", recipient_private_key=None, now: datetime | None = None) -> bytes:
    tl.assert_unlocked(c["unlock_timestamp"], now)          # 1) cek waktu dulu
    if c.get("hybrid"):                                      # 2) kunci dasar
        if recipient_private_key is None:
            raise cc.DecryptionError("Kapsul hibrida: private key penerima diperlukan.")
        base = cc.unwrap_session_key(cc.from_b64(c["hybrid"]["wrapped_session_key"]), recipient_private_key)
    else:
        base, _ = cc.derive_key(password, salt=cc.from_b64(c["salt"]))
    key = _final_key(base, c["id"], c["unlock_timestamp"])   # 3) dekripsi + verifikasi tag
    return ALGOS[c["algorithm"]][1](cc.from_b64(c["ciphertext"]), key, cc.from_b64(c["nonce"]), _aad(c))


def capsule_to_json(c: dict) -> str:
    return json.dumps(c, indent=2)


def capsule_from_json(t: str) -> dict:
    return json.loads(t)


def tamper_ciphertext(c: dict, byte_index: int = 0) -> dict:
    t, raw = dict(c), bytearray(cc.from_b64(c["ciphertext"]))
    raw[byte_index % len(raw)] ^= 0xFF
    t["ciphertext"] = cc.to_b64(bytes(raw))
    return t
