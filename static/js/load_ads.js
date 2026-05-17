const adEl = document.getElementById('header-pub');
if (adEl) {
  fetch(adEl.dataset.adUrl)
    .then(r => r.text())
    .then(html => {
      if (html.trim()) {
        adEl.innerHTML = html;
      } else {
        adEl.remove();
      }
    });
}
