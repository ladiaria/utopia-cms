const adEl = document.getElementById('header-pub');
if (adEl) {
  fetch(adEl.dataset.adUrl)
    .then(r => r.text())
    .then(html => { adEl.innerHTML = html; });
}
