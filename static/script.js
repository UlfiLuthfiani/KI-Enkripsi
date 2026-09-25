const $ = (i) => document.getElementById(i);

// ---- pindah tab ----
function tab(n) {
  for (const i of [1, 2]) {
    $('p' + i).classList.toggle('hide', i !== n);
    $('t' + i).setAttribute('aria-selected', i === n);
  }
}
$('t1').onclick = () => tab(1);
$('t2').onclick = () => tab(2);

// ---- tampilkan input teks vs input berkas ----
$('kind').onchange = (e) => {
  $('textBox').classList.toggle('hide', e.target.value !== 'text');
  $('fileBox').classList.toggle('hide', e.target.value !== 'file');
};

// ---- util ----
const readB64 = (f) => new Promise((r) => {
  const x = new FileReader();
  x.onload = () => r(x.result.split(',')[1]);
  x.readAsDataURL(f);
});

const show = (id, cls, t) => {
  $(id).innerHTML = `<div class="msg ${cls}"></div>`;
  $(id).firstChild.textContent = t;
};

async function post(u, b) {
  try {
    const r = await fetch(u, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(b),
    });
    let j = {};
    try { j = await r.json(); } catch {}
    return { s: r.status, j };
  } catch (err) {
    // server mati / tidak bisa dihubungi / masalah jaringan
    return { s: 0, j: { detail: 'Tidak bisa menghubungi server. Cek apakah server sedang berjalan.' } };
  }
}

// Bikin tombol otomatis "loading" (disabled + teks berubah) selagi proses,
// supaya orang tidak klik berkali-kali dan tahu aplikasinya sedang bekerja.
function withLoading(button, label, fn) {
  return async (...args) => {
    const teksAsli = button.textContent;
    button.disabled = true;
    button.textContent = label;
    try {
      await fn(...args);
    } finally {
      button.disabled = false;
      button.textContent = teksAsli;
    }
  };
}

// ===================== PRATINJAU BERKAS (gambar & cover PDF) =====================
const IMG_EXT = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'];

function extOf(filename) {
  return (filename.split('.').pop() || '').toLowerCase();
}

function base64ToBlob(base64, mime = 'application/octet-stream') {
  const raw = atob(base64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

function makeDownloadLink(filename, base64) {
  const a = document.createElement('a');
  a.className = 'dl';
  a.textContent = 'Unduh ' + filename;
  a.download = filename;
  a.href = URL.createObjectURL(base64ToBlob(base64));
  return a;
}

async function renderPdfCover(base64, container) {
  if (!window['pdfjsLib']) {
    container.append('(Pratinjau PDF tidak tersedia, koneksi ke CDN gagal.)');
    return;
  }
  const raw = atob(base64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);

  const pdf = await pdfjsLib.getDocument({ data: bytes }).promise;
  const page = await pdf.getPage(1);
  const viewport = page.getViewport({ scale: 1.0 });

  const maxWidth = 320;
  const scale = maxWidth / viewport.width;
  const scaledViewport = page.getViewport({ scale });

  const canvas = document.createElement('canvas');
  canvas.className = 'preview-pdf-canvas';
  canvas.width = scaledViewport.width;
  canvas.height = scaledViewport.height;

  await page.render({ canvasContext: canvas.getContext('2d'), viewport: scaledViewport }).promise;
  container.append(canvas);
}

const MIME_BY_EXT = {
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg',
  gif: 'image/gif', webp: 'image/webp', bmp: 'image/bmp', svg: 'image/svg+xml',
};

function renderImage(base64, filename, container) {
  const ext = extOf(filename);
  const mime = MIME_BY_EXT[ext] || 'image/png';
  const img = document.createElement('img');
  img.className = 'preview-img';
  img.src = URL.createObjectURL(base64ToBlob(base64, mime));
  container.append(img);
}

// Fungsi utama: dipanggil setelah kapsul berhasil dibuka dan isinya berkas.
async function renderOpenedFile(filename, base64, container) {
  const ext = extOf(filename);
  const dl = makeDownloadLink(filename, base64);
  container.append(document.createElement('br'), dl);

  if (IMG_EXT.includes(ext)) {
    renderImage(base64, filename, container);
  } else if (ext === 'pdf') {
    try {
      await renderPdfCover(base64, container);
    } catch (e) {
      container.append(document.createElement('br'), '(Gagal membuat pratinjau PDF: ' + e.message + ')');
    }
  }
  // jenis lain: cukup tombol unduh saja, tidak ada pratinjau
}

// ===================== SEGEL KAPSUL =====================
$('seal').onclick = withLoading($('seal'), 'Menyegel...', async () => {
  if (!$('when').value) {
    return show('sealOut', 'err', 'Pilih tanggal dan jam kapsul boleh dibuka.');
  }

  const b = {
    password: $('pw').value,
    algorithm: $('algo').value,
    unlock_iso: new Date($('when').value).toISOString(),
    public_key_pem: $('pub').value || null,
  };

  if ($('kind').value === 'text') {
    b.text = $('msg').value;
  } else {
    const f = $('file').files[0];
    if (!f) return show('sealOut', 'err', 'Pilih berkas dulu.');
    b.file_b64 = await readB64(f);
    b.filename = f.name;
  }

  const { s, j } = await post('/api/seal', b);
  if (s !== 200) {
    return show('sealOut', 'err', j.detail || 'Gagal menyegel kapsul.');
  }

  const txt = JSON.stringify(j, null, 2);
  const waktu = new Date(j.unlock_timestamp * 1000).toLocaleString('id-ID');

  $('sealOut').innerHTML =
    '<div class="msg ok">Kapsul tersegel. Baru bisa dibuka pada ' + waktu +
    '.<br><a class="dl" download="surat_masa_depan.kapsul"></a></div>' +
    '<textarea readonly></textarea>';

  const a = $('sealOut').querySelector('a');
  a.textContent = 'Unduh berkas .kapsul';
  a.href = URL.createObjectURL(new Blob([txt], { type: 'application/json' }));
  $('sealOut').querySelector('textarea').value = txt;
});

// ---- info singkat saat JSON kapsul ditempel/diunggah ----
function info() {
  try {
    const c = JSON.parse($('capIn').value);
    const waktu = new Date(c.unlock_timestamp * 1000).toLocaleString('id-ID');
    $('capInfo').innerHTML = '<small></small>';
    $('capInfo').firstChild.textContent = c.algorithm + ' · dibuka mulai ' + waktu;
  } catch {
    $('capInfo').innerHTML = '';
  }
}
$('capIn').oninput = info;
$('capFile').onchange = async (e) => {
  $('capIn').value = await e.target.files[0].text();
  info();
};

// ===================== BUKA KAPSUL =====================
$('open').onclick = withLoading($('open'), 'Membuka...', async () => {
  let c;
  try {
    c = JSON.parse($('capIn').value);
  } catch {
    return show('openOut', 'err', 'Isi kapsul bukan JSON yang valid.');
  }

  const { s, j } = await post('/api/open', {
    capsule: c,
    password: $('pw2').value,
    private_key_pem: $('priv').value || null,
  });

  if (s === 423) {
    // belum waktunya: server mengirim unix timestamp mentah,
    // dikonversi ke jam lokal browser di sini
    const t = new Date(Number(j.detail) * 1000);
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return show('openOut', 'wait',
      'Belum waktunya. Baru bisa dibuka pada ' + t.toLocaleString('id-ID') + ' (' + tz + ').');
  }
  if (s === 401) {
    return show('openOut', 'err', 'Gagal dibuka. ' + j.detail);
  }
  if (s !== 200) {
    return show('openOut', 'err', j.detail || 'Kapsul tidak valid.');
  }

  show('openOut', 'ok', j.is_file ? 'Kapsul terbuka. Berkas: ' + j.filename : j.text);

  if (j.is_file) {
    await renderOpenedFile(j.filename, j.file_b64, $('openOut').firstChild);
  }
});