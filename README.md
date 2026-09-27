## Anggota Kelompok

Ulfi Luthfiani 247006111006
Yulita Rahayu 247006111035
Nayla Qurrota Aini 247006111043


# Surat untuk Masa Depan (Kapsul Waktu Digital)

Aplikasi web untuk mengenkripsi pesan teks maupun berkas (gambar, PDF, dll) dan
menguncinya hingga waktu tertentu di masa depan ("time-lock"). Selama waktu
buka belum tercapai, kapsul tidak bisa didekripsi oleh siapa pun termasuk
pembuatnya sendiri meskipun kata sandinya benar.


## Fitur

- Enkripsi simetris modern: **AES-256-GCM** dan **ChaCha20-Poly1305**, untuk
  teks maupun berkas (gambar, PDF, dan lainnya)
- Kunci diturunkan dari kata sandi memakai **Argon2id** dengan salt acak
- Nonce/IV dibangkitkan acak pada setiap enkripsi dan disimpan bersama
  cipherteks
- Cipherteks ditampilkan dan bisa disalin/diunduh dalam format Base64 (di
  dalam berkas "kapsul" berformat JSON)
- Dekripsi ditolak jika kata sandi salah atau cipherteks/metadata telah
  diubah (verifikasi tag AEAD gagal)
- Mekanisme time-lock: kunci akhir diturunkan dari gabungan kunci kata sandi
  dan kunci waktu (HMAC bertanda server), sehingga mengubah `unlock_timestamp`
  pada JSON kapsul tidak bisa memaksa kapsul terbuka lebih awal
- **Fitur pengayaan:** enkripsi hibrida — kunci sesi AES dibangkitkan acak
  lalu dibungkus dengan **RSA-OAEP** memakai kunci publik penerima, sehingga
  kapsul bisa dibuka tanpa kata sandi bersama, cukup dengan kunci privat
  penerima


## Cara Instalasi

**Prasyarat:** Python 3.11 atau lebih baru.

1. Clone repositori dan masuk ke foldernya
   ```bash
   git clone <URL-repositori-ini>
   cd KI-Enkripsi
   ```

2. (Disarankan) Buat dan aktifkan virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

3. Pasang dependensi
   ```bash
   pip install -r requirements.txt
   ```

4. Buat berkas `.env` di root proyek berisi kunci rahasia untuk mekanisme
   time-lock (bebas diisi string acak apa saja, jangan dibagikan/diunggah):
   ```bash
   echo "TIMELOCK_SECRET=ganti-dengan-string-acak-rahasia-anda" > .env
   ```

## Cara Menjalankan

Jalankan server API + web dengan Uvicorn:

```bash
uvicorn server:app --reload
```

Lalu buka `http://127.0.0.1:8000` di peramban.

## Contoh Penggunaan

### Lewat antarmuka web

1. Buka tab **Tulis Surat**, pilih jenis pesan (teks atau berkas), isi kata
   sandi, pilih algoritma (AES-256-GCM atau ChaCha20-Poly1305), tentukan
   tanggal/jam kapsul boleh dibuka, lalu klik **Segel Surat**.
2. Hasilnya berupa kapsul terenkripsi (JSON berisi cipherteks Base64, nonce,
   salt, dan metadata) yang bisa disalin atau diunduh.
3. Buka tab **Buka Surat**, tempelkan/unggah kapsul tadi, masukkan kata
   sandi yang sama, lalu klik **Buka Surat**.
   - Sebelum waktu buka tercapai → ditolak (terkunci waktu).
   - Kata sandi salah atau isi kapsul diubah → ditolak (verifikasi gagal).
   - Kata sandi benar dan waktu sudah tercapai → pesan/berkas asli tampil.

### Mode hibrida (RSA-OAEP)

Pada tab **Tulis Surat**, buka bagian **Enkripsi hibrida (opsional)** dan
tempelkan kunci publik (PEM) penerima — kata sandi tidak perlu diisi. Saat
membuka, penerima menempelkan kunci privat (PEM) miliknya pada tab
**Buka Surat**. Contoh pasangan kunci uji tersedia di `public.pem` dan
`private.pem` 

## Menjalankan Pengujian Kuantitatif

Skrip `testing.py` menjalankan seluruh pengujian wajib tugas (kebenaran
dekripsi ≥10 masukan termasuk gambar & PDF, waktu proses untuk berkas 1 KB/1
MB/10 MB, avalanche effect, entropi & histogram byte, serta perbandingan
AES-256-GCM vs ChaCha20-Poly1305), lalu mengekspor hasilnya ke
`outputs/hasil_pengujian.xlsx` dan grafik `.png`.

```bash
# Pilih berkas uji (gambar & PDF) lewat jendela dialog
python testing.py

# Atau tentukan berkas uji langsung lewat argumen
python testing.py --file contoh.png contoh.pdf --no-dialog
```



