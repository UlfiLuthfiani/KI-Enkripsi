// extras.js
// Hanya berisi hal kosmetik (tampilan), TIDAK ada logika enkripsi/segel/buka
// di sini. Semua fungsi inti tetap ada di script.js dan tidak diubah.

// ---- 1) Efek judul melengkung ala tulisan tangan ----
function arcifyTitle(el, spread = 16, rise = 16) {
  const text = el.textContent;
  el.textContent = '';
  const chars = [...text];
  const n = chars.length;
  chars.forEach((ch, i) => {
    const t = n > 1 ? (i - (n - 1) / 2) / ((n - 1) / 2) : 0; // -1..1
    const rotate = t * spread;
    const lift = (1 - t * t) * rise;
    const span = document.createElement('span');
    span.textContent = ch === ' ' ? '\u00A0' : ch;
    span.style.transform = `translateY(${-lift}px) rotate(${rotate}deg)`;
    el.appendChild(span);
  });
}
document.querySelectorAll('.arc-title').forEach((el) => arcifyTitle(el));

// ---- 2) Tombol mata untuk tampilkan/sembunyikan kata sandi ----
document.querySelectorAll('.eye-toggle').forEach((btn) => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
  });
});
