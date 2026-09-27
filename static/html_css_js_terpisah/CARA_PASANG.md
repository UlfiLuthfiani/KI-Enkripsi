CARA PASANG — index.html, style.css, script.js hasil pemisahan
=============================================================================

LANGKAH 1 — Ganti 3 file di folder static/ dengan yang baru
=============================================================================
Timpa file-file ini di project kamu:
  static/index.html   <- versi baru, sudah link ke style.css & script.js
  static/style.css    <- BARU, isi CSS yang dulu nempel di <style>
  static/script.js    <- BARU, isi JS yang dulu nempel di <script>,
                          SUDAH ditambah fitur pratinjau gambar & cover PDF

=============================================================================
LANGKAH 2 — WAJIB: tambahkan static file mount di server.py
=============================================================================
Tanpa langkah ini, browser akan gagal memuat style.css & script.js (404),
karena FastAPI sekarang cuma tahu cara mengirim index.html, belum tahu cara
mengirim file lain di folder static/.

Buka server.py, tambahkan import ini di bagian atas:

    from fastapi.staticfiles import StaticFiles

Lalu, PERSIS SETELAH baris `app = FastAPI(...)`, tambahkan:

    app.mount("/static", StaticFiles(directory="static"), name="static")

Jangan taruh baris mount ini SEBELUM endpoint-endpoint lain (/api/login,
/api/seal, dst) kalau menggunakan urutan route tertentu — tapi untuk kasus
ini aman ditaruh di mana saja setelah `app = FastAPI(...)` karena path-nya
"/static/..." tidak akan bentrok dengan endpoint "/api/...".

=============================================================================
LANGKAH 3 — Jalankan & coba
=============================================================================
    uvicorn server:app --reload

Buka localhost:8000, tekan Ctrl+Shift+R (hard refresh) supaya cache lama
tidak kepakai. Buka DevTools (F12) -> tab Network -> pastikan style.css dan
script.js muncul dengan status 200, bukan 404.

Kalau muncul 404 untuk style.css/script.js -> berarti langkah 2 belum
kepasang dengan benar, cek lagi baris app.mount di server.py.

=============================================================================
CATATAN
=============================================================================
- Semua fungsi lama TIDAK berubah perilakunya (segel, buka, tab, dsb),
  cuma dipindah lokasi filenya + ditambah fitur pratinjau berkas.
- Kalau nanti mau ubah tampilan, cukup edit style.css.
  Kalau mau ubah logika, cukup edit script.js.
  index.html sekarang isinya cuma struktur halaman doang, lebih rapi
  buat dibagi kerjaannya kalau kerja bertiga (satu orang pegang CSS, satu
  pegang JS, satu pegang HTML/struktur, tanpa saling tabrakan edit file).
