import os
os.environ.setdefault("TIMELOCK_SECRET", "rahasia-uji-bukan-produksi")
from datetime import datetime, timedelta, timezone
import pytest
from modules import capsule as cap, crypto_core as cc, timelock as tl

PAST = datetime.now(timezone.utc) - timedelta(days=1)
FUTURE = datetime.now(timezone.utc) + timedelta(days=1825)


@pytest.mark.parametrize("algo", ["AES-256-GCM", "ChaCha20-Poly1305"])
def test_roundtrip(algo):
    c = cap.create_capsule(b"halo masa depan", "pw", PAST, algo)
    assert cap.open_capsule(c, "pw") == b"halo masa depan"


def test_wrong_password_rejected():
    c = cap.create_capsule(b"x", "benar", PAST)
    with pytest.raises(cc.DecryptionError):
        cap.open_capsule(c, "salah")


def test_tampered_ciphertext_rejected():
    c = cap.create_capsule(b"pesan", "pw", PAST)
    with pytest.raises(cc.DecryptionError):
        cap.open_capsule(cap.tamper_ciphertext(c), "pw")


def test_too_early_even_with_correct_password():
    c = cap.create_capsule(b"x", "pw", FUTURE)
    with pytest.raises(tl.TimeLockedError):
        cap.open_capsule(c, "pw")


def test_editing_unlock_timestamp_does_not_bypass():
    c = cap.create_capsule(b"x", "pw", FUTURE)
    c["unlock_timestamp"] = 0
    with pytest.raises(cc.DecryptionError):
        cap.open_capsule(c, "pw")


def test_nonce_and_salt_random():
    a, b = cap.create_capsule(b"x", "pw", PAST), cap.create_capsule(b"x", "pw", PAST)
    assert a["nonce"] != b["nonce"] and a["salt"] != b["salt"]


def test_hybrid_roundtrip_and_wrong_key():
    priv, pub = cc.generate_rsa_keypair()
    c = cap.create_capsule(b"untukmu", "", PAST, recipient_public_key=pub)
    assert cap.open_capsule(c, recipient_private_key=priv) == b"untukmu"
    other, _ = cc.generate_rsa_keypair()
    with pytest.raises(cc.DecryptionError):
        cap.open_capsule(c, recipient_private_key=other)
