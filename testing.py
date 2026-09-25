"""
testing.py
Skrip pengujian wajib untuk laporan UTS:
1. Kebenaran dekripsi pada >=10 masukan berbeda (termasuk gambar & PDF)
2. Waktu enkripsi/dekripsi untuk 1 KB, 1 MB, 10 MB
3. Avalanche effect (perubahan 1 bit plaintext / key)
4. Entropi & histogram byte cipherteks vs plainteks
5. Perbandingan AES-256-GCM vs ChaCha20-Poly1305

Jalankan: python testing.py            (muncul jendela pilih file)
         python testing.py --file a.pdf b.png
         python testing.py --no-dialog   (pakai berkas contoh di test_files/)
Hasil (grafik & ringkasan) disimpan ke folder outputs/.
"""

import os
import time
import math
import hashlib
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook

from modules import crypto_core as cc

OUTPUT_DIR = "outputs"
TEST_FILES_DIR = "test_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _buat_berkas_contoh():
    """Membuat PNG & PDF contoh di test_files/ bila belum ada (dipakai sebagai cadangan)."""
    png_path = os.path.join(TEST_FILES_DIR, "test_image.png")
    pdf_path = os.path.join(TEST_FILES_DIR, "test_document.pdf")
    if not (os.path.exists(png_path) and os.path.exists(pdf_path)):
        os.makedirs(TEST_FILES_DIR, exist_ok=True)
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.bar(["AES-GCM", "ChaCha20"], [92, 88], color=["#1f4fbf", "#c92f27"])
        ax.set_title("Berkas Uji - Kapsul Waktu Digital")
        plt.tight_layout(); plt.savefig(png_path, dpi=100); plt.close()

        fig, ax = plt.subplots(figsize=(6, 4)); ax.axis("off")
        ax.text(0.5, 0.6, "Dokumen Uji", ha="center", fontsize=20, weight="bold")
        ax.text(0.5, 0.45, "Surat untuk Masa Depan - Kapsul Waktu Digital", ha="center", fontsize=11)
        plt.savefig(pdf_path); plt.close()
    return [png_path, pdf_path]


def pilih_berkas_uji(argumen_file, pakai_dialog=True):
    """
    Menentukan berkas uji (gambar, PDF, dll) dengan urutan prioritas:
      1. argumen --file di command line
      2. jendela pilih file (tkinter) dari laptop, boleh pilih banyak berkas
      3. berkas contoh di test_files/ (bila dialog dibatalkan / tidak tersedia)
    Mengembalikan daftar (nama_berkas, isi_bytes).
    """
    paths = list(argumen_file or [])

    if not paths and pakai_dialog:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)  # supaya jendela pilih file tidak tertutup
            paths = list(filedialog.askopenfilenames(
                title="Pilih berkas uji (gambar / PDF / lainnya) - boleh pilih beberapa",
                filetypes=[("Gambar & PDF", "*.png *.jpg *.jpeg *.bmp *.gif *.pdf"),
                           ("Semua berkas", "*.*")],
            ))
            root.destroy()
        except Exception as e:
            print(f"  (Jendela pilih file tidak tersedia: {e}. Memakai berkas contoh.)")

    if not paths:
        print("  Tidak ada berkas dipilih -> memakai berkas contoh di test_files/")
        paths = _buat_berkas_contoh()

    berkas = []
    for p in paths:
        with open(p, "rb") as f:
            berkas.append((os.path.basename(p), f.read()))

    ada_gambar = any(n.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")) for n, _ in berkas)
    ada_pdf = any(n.lower().endswith(".pdf") for n, _ in berkas)
    if not (ada_gambar and ada_pdf):
        print("  PERINGATAN: syarat tugas meminta pengujian berkas gambar DAN PDF. "
              "Pastikan keduanya ikut terpilih (bisa jalankan ulang).")
    return berkas


# ---------------------------------------------------------------------------
# 1. Kebenaran dekripsi pada berbagai masukan
# ---------------------------------------------------------------------------
def test_kebenaran_dekripsi(berkas_uji):
    print("=" * 70)
    print("1. UJI KEBENARAN DEKRIPSI (10+ masukan)")
    print("=" * 70)

    test_inputs = [
        ("teks pendek", b"Halo dunia"),
        ("teks kosong", b""),
        ("teks panjang", ("Lorem ipsum dolor sit amet. " * 200).encode()),
        ("teks unicode", "Halo 你好 مرحبا 🎉".encode("utf-8")),
        ("biner acak kecil", os.urandom(64)),
        ("biner acak 1KB", os.urandom(1024)),
        ("biner acak 10KB", os.urandom(10 * 1024)),
        ("data JSON", b'{"nama": "budi", "nik": "1234567890123456"}'),
        ("satu byte", b"\x00"),
        ("data 100KB", os.urandom(100 * 1024)),
    ]
    # berkas asli pilihan pengguna (gambar, PDF, dll) ikut diuji
    for nama_berkas, isi in berkas_uji:
        test_inputs.append((f"berkas: {nama_berkas} ({len(isi)} byte)", isi))

    key, salt = cc.derive_key("password_uji")
    hasil_semua = []

    for nama, data in test_inputs:
        hash_asli = hashlib.sha256(data).hexdigest()
        for algo_name, enc_fn, dec_fn in [
            ("AES-256-GCM", cc.encrypt_aes_gcm, cc.decrypt_aes_gcm),
            ("ChaCha20-Poly1305", cc.encrypt_chacha20, cc.decrypt_chacha20),
        ]:
            ciphertext, nonce = enc_fn(data, key)
            decrypted = dec_fn(ciphertext, key, nonce)
            # dibandingkan lewat SHA-256, bukan cuma "==", supaya jelas bahwa berkas
            # gambar/PDF asli utuh byte-per-byte setelah dekripsi (bukan cuma sama isi)
            sukses = hashlib.sha256(decrypted).hexdigest() == hash_asli
            hasil_semua.append((nama, algo_name, sukses))
            status = "OK" if sukses else "GAGAL"
            print(f"  [{status}] {nama:58s} | {algo_name}")

    total = len(hasil_semua)
    sukses_count = sum(1 for _, _, s in hasil_semua if s)
    print(f"\nRingkasan: {sukses_count}/{total} pengujian berhasil.\n")
    return hasil_semua


# ---------------------------------------------------------------------------
# 2. Waktu enkripsi/dekripsi untuk berbagai ukuran berkas
# ---------------------------------------------------------------------------
def test_waktu_proses():
    print("=" * 70)
    print("2. UJI WAKTU ENKRIPSI/DEKRIPSI (1KB, 1MB, 10MB)")
    print("=" * 70)

    ukuran = {"1 KB": 1024, "1 MB": 1024 * 1024, "10 MB": 10 * 1024 * 1024}
    key, _ = cc.derive_key("password_uji")

    hasil = {}
    for label, size in ukuran.items():
        data = os.urandom(size)
        hasil[label] = {}
        for algo_name, enc_fn, dec_fn in [
            ("AES-256-GCM", cc.encrypt_aes_gcm, cc.decrypt_aes_gcm),
            ("ChaCha20-Poly1305", cc.encrypt_chacha20, cc.decrypt_chacha20),
        ]:
            t0 = time.perf_counter()
            ciphertext, nonce = enc_fn(data, key)
            t1 = time.perf_counter()
            _ = dec_fn(ciphertext, key, nonce)
            t2 = time.perf_counter()

            enc_time = (t1 - t0) * 1000  # ms
            dec_time = (t2 - t1) * 1000  # ms
            hasil[label][algo_name] = (enc_time, dec_time)
            print(f"  {label:6s} | {algo_name:18s} | enkripsi: {enc_time:8.3f} ms | dekripsi: {dec_time:8.3f} ms")

    # Grafik
    labels = list(ukuran.keys())
    x = range(len(labels))
    width = 0.2
    fig, ax = plt.subplots(figsize=(8, 5))
    for i, algo in enumerate(["AES-256-GCM", "ChaCha20-Poly1305"]):
        enc_vals = [hasil[l][algo][0] for l in labels]
        dec_vals = [hasil[l][algo][1] for l in labels]
        ax.bar([p + i * width for p in x], enc_vals, width, label=f"{algo} (enkripsi)")
        ax.bar([p + i * width for p in x], dec_vals, width, bottom=enc_vals, label=f"{algo} (dekripsi)", alpha=0.6)
    ax.set_xticks([p + width / 2 for p in x])
    ax.set_xticklabels(labels)
    ax.set_ylabel("Waktu (ms)")
    ax.set_title("Waktu Enkripsi/Dekripsi berdasarkan Ukuran Berkas")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/waktu_proses.png", dpi=150)
    plt.close()
    print(f"\nGrafik disimpan: {OUTPUT_DIR}/waktu_proses.png\n")
    return hasil


# ---------------------------------------------------------------------------
# 3. Avalanche effect
# ---------------------------------------------------------------------------
def hamming_distance_bits(a: bytes, b: bytes) -> int:
    """Menghitung jumlah bit yang berbeda antara dua bytes dengan panjang sama."""
    assert len(a) == len(b)
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def test_avalanche_effect():
    print("=" * 70)
    print("3. UJI AVALANCHE EFFECT")
    print("=" * 70)

    plaintext = os.urandom(256)
    key, _ = cc.derive_key("password_uji", salt=os.urandom(16))

    hasil = {}
    for algo_name, enc_fn in [
        ("AES-256-GCM", cc.encrypt_aes_gcm),
        ("ChaCha20-Poly1305", cc.encrypt_chacha20),
    ]:
        # Perubahan 1 bit pada plaintext (nonce dipertahankan sama utk perbandingan adil)
        ciphertext1, nonce = enc_fn(plaintext, key)

        plaintext_modified = bytearray(plaintext)
        plaintext_modified[0] ^= 0x01  # flip 1 bit
        # gunakan nonce yang sama secara manual untuk perbandingan avalanche yang adil
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
        if algo_name == "AES-256-GCM":
            ciphertext2 = AESGCM(key).encrypt(nonce, bytes(plaintext_modified), b"")
        else:
            ciphertext2 = ChaCha20Poly1305(key).encrypt(nonce, bytes(plaintext_modified), b"")

        min_len = min(len(ciphertext1), len(ciphertext2))
        diff_bits = hamming_distance_bits(ciphertext1[:min_len], ciphertext2[:min_len])
        total_bits = min_len * 8
        persen_plaintext = (diff_bits / total_bits) * 100

        # Perubahan 1 bit pada key
        key_modified = bytearray(key)
        key_modified[0] ^= 0x01
        if algo_name == "AES-256-GCM":
            ciphertext3 = AESGCM(bytes(key_modified)).encrypt(nonce, plaintext, b"")
        else:
            ciphertext3 = ChaCha20Poly1305(bytes(key_modified)).encrypt(nonce, plaintext, b"")

        diff_bits_key = hamming_distance_bits(ciphertext1[:min_len], ciphertext3[:min_len])
        persen_key = (diff_bits_key / total_bits) * 100

        hasil[algo_name] = {"plaintext_bit_flip": persen_plaintext, "key_bit_flip": persen_key}
        print(f"  {algo_name}:")
        print(f"    - Flip 1 bit plaintext -> {persen_plaintext:.2f}% bit cipherteks berubah")
        print(f"    - Flip 1 bit key       -> {persen_key:.2f}% bit cipherteks berubah")

    print("\n  Idealnya avalanche effect mendekati 50% (perubahan acak/tidak terprediksi).\n")
    return hasil


# ---------------------------------------------------------------------------
# 4. Entropi & histogram byte
# ---------------------------------------------------------------------------
def calc_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counter = Counter(data)
    length = len(data)
    entropy = 0.0
    for count in counter.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def test_entropi_histogram():
    print("=" * 70)
    print("4. UJI ENTROPI & HISTOGRAM BYTE")
    print("=" * 70)

    # Plaintext yang polanya jelas terlihat (bukan acak) agar kontrasnya jelas
    plaintext = ("Ini adalah contoh teks biasa yang polanya jelas terlihat dan tidak acak. " * 50).encode()
    key, _ = cc.derive_key("password_uji")
    ciphertext, nonce = cc.encrypt_aes_gcm(plaintext, key)

    ent_plain = calc_entropy(plaintext)
    ent_cipher = calc_entropy(ciphertext)

    print(f"  Entropi plaintext : {ent_plain:.4f} bit/byte (maks 8.0)")
    print(f"  Entropi cipherteks: {ent_cipher:.4f} bit/byte (maks 8.0)")
    print(f"  -> Cipherteks yang baik harus mendekati 8.0 (distribusi byte seragam/acak)\n")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].hist(list(plaintext), bins=256, range=(0, 255), color="steelblue")
    axes[0].set_title(f"Histogram Byte Plaintext\n(Entropi = {ent_plain:.2f} bit/byte)")
    axes[0].set_xlabel("Nilai byte (0-255)")
    axes[0].set_ylabel("Frekuensi")

    axes[1].hist(list(ciphertext), bins=256, range=(0, 255), color="indianred")
    axes[1].set_title(f"Histogram Byte Cipherteks\n(Entropi = {ent_cipher:.2f} bit/byte)")
    axes[1].set_xlabel("Nilai byte (0-255)")
    axes[1].set_ylabel("Frekuensi")

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/entropi_histogram.png", dpi=150)
    plt.close()
    print(f"Grafik disimpan: {OUTPUT_DIR}/entropi_histogram.png\n")
    return ent_plain, ent_cipher


# ---------------------------------------------------------------------------
# 5. Ekspor semua hasil ke satu berkas Excel (syarat luaran "Data pengujian")
# ---------------------------------------------------------------------------
def ekspor_xlsx(kebenaran, waktu, avalanche, entropi):
    wb = Workbook()

    ws = wb.active
    ws.title = "Kebenaran Dekripsi"
    ws.append(["Masukan", "Algoritma", "Berhasil"])
    for nama, algo, sukses in kebenaran:
        ws.append([nama, algo, "Ya" if sukses else "TIDAK"])

    ws2 = wb.create_sheet("Waktu Proses")
    ws2.append(["Ukuran Berkas", "Algoritma", "Waktu Enkripsi (ms)", "Waktu Dekripsi (ms)"])
    for ukuran, per_algo in waktu.items():
        for algo, (t_enc, t_dec) in per_algo.items():
            ws2.append([ukuran, algo, round(t_enc, 3), round(t_dec, 3)])

    ws3 = wb.create_sheet("Avalanche Effect")
    ws3.append(["Algoritma", "Flip 1 bit plaintext (%)", "Flip 1 bit key (%)"])
    for algo, v in avalanche.items():
        ws3.append([algo, round(v["plaintext_bit_flip"], 3), round(v["key_bit_flip"], 3)])

    ws4 = wb.create_sheet("Entropi")
    ent_plain, ent_cipher = entropi
    ws4.append(["Jenis Data", "Entropi (bit/byte)", "Maksimum Teoretis"])
    ws4.append(["Plaintext", round(ent_plain, 4), 8.0])
    ws4.append(["Cipherteks (AES-256-GCM)", round(ent_cipher, 4), 8.0])

    path = os.path.join(OUTPUT_DIR, "hasil_pengujian.xlsx")
    wb.save(path)
    print(f"Data pengujian diekspor ke: {path}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pengujian kriptografi Kapsul Waktu Digital")
    parser.add_argument("--file", nargs="+", metavar="BERKAS",
                        help="berkas uji (gambar/PDF/dll), boleh lebih dari satu")
    parser.add_argument("--no-dialog", action="store_true",
                        help="jangan buka jendela pilih file; pakai berkas contoh di test_files/")
    args = parser.parse_args()

    berkas_uji = pilih_berkas_uji(args.file, pakai_dialog=not args.no_dialog)
    hasil_kebenaran = test_kebenaran_dekripsi(berkas_uji)
    hasil_waktu = test_waktu_proses()
    hasil_avalanche = test_avalanche_effect()
    hasil_entropi = test_entropi_histogram()
    ekspor_xlsx(hasil_kebenaran, hasil_waktu, hasil_avalanche, hasil_entropi)
    print("=" * 70)
    print("SEMUA PENGUJIAN WAJIB SELESAI.")
    print("Grafik  -> outputs/*.png")
    print("Data uji -> outputs/hasil_pengujian.xlsx")
    print("=" * 70)