"""
timelock.py
Mekanisme "kapsul waktu": kapsul hanya boleh didekripsi setelah tanggal
tertentu tercapai, terlepas dari benar tidaknya password.

Catatan implementasi (penting untuk laporan):
Ini BUKAN time-lock cryptography sejati (seperti Verifiable Delay Function),
melainkan pengecekan waktu di level aplikasi terhadap timestamp yang
tersimpan pada metadata kapsul. Simplifikasi ini diambil secara sadar
karena time-lock puzzle kriptografis murni berada di luar cakupan mata
kuliah ini. Nilai keamanan intinya tetap dijaga oleh AES-256-GCM /
ChaCha20-Poly1305 dan Argon2id.
"""

from datetime import datetime, timezone


class TimeLockedError(Exception):
    """Dilempar ketika kapsul belum boleh dibuka karena waktu belum tercapai."""
    pass


def make_unlock_timestamp(dt: datetime) -> int:
    """Mengubah objek datetime menjadi unix timestamp (UTC) untuk disimpan di metadata."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def is_unlocked(unlock_timestamp: int, now: datetime | None = None) -> bool:
    """Mengecek apakah waktu sekarang sudah melewati unlock_timestamp."""
    now = now or datetime.now(timezone.utc)
    return int(now.timestamp()) >= unlock_timestamp


def assert_unlocked(unlock_timestamp: int, now: datetime | None = None) -> None:
    """Raise TimeLockedError jika kapsul belum boleh dibuka."""
    if not is_unlocked(unlock_timestamp, now):
        unlock_dt = datetime.fromtimestamp(unlock_timestamp, tz=timezone.utc)
        raise TimeLockedError(
            f"Kapsul belum boleh dibuka. Baru dapat dibuka pada "
            f"{unlock_dt.strftime('%d %B %Y %H:%M UTC')}."
        )


def time_remaining_str(unlock_timestamp: int, now: datetime | None = None) -> str:
    """Mengembalikan string sisa waktu yang manusiawi, misal '2 hari 3 jam lagi'."""
    now = now or datetime.now(timezone.utc)
    delta = datetime.fromtimestamp(unlock_timestamp, tz=timezone.utc) - now
    if delta.total_seconds() <= 0:
        return "Sudah bisa dibuka"
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} hari")
    if hours:
        parts.append(f"{hours} jam")
    if minutes and not days:
        parts.append(f"{minutes} menit")
    return " ".join(parts) + " lagi" if parts else "Kurang dari 1 menit lagi"
