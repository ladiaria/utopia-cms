function read_later_events(articleContentTypeId, container) {
  const scope = container ? container : document;

  const outlinedSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 16 16"><path fill="#999" d="M4.13 3c-.616 0-1.125.496-1.125 1.099L3 14l4.5-1.65L12 14V4.1c0-.601-.51-1.1-1.125-1.1zm0 1.1h6.745v8.312L7.5 11.175l-3.374 1.237z"/></svg>`;
  const filledSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 16 16"><g clip-path="url(#clip0_3724_20441)"><path fill="#000" stroke="#000" stroke-width="1.5" d="M4.666 2.75h6.667c.322 0 .583.261.583.583v9.53L8.69 11.48a1.75 1.75 0 0 0-1.38 0l-3.227 1.382V3.333c0-.322.262-.583.583-.583Z"/></g><defs><clipPath id="clip0_3724_20441"><path fill="#fff" d="M0 0h16v16H0z"/></clipPath></defs></svg>`;

  scope.querySelectorAll(".ld-card__addtrl").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const articleId = btn.dataset.articleId;
      const isAdded = btn.classList.contains("added");
      const action = isAdded ? "unfollow" : "follow";

      fetch(`/activity/${action}/${articleContentTypeId}/${articleId}/`)
        .then(function () {
          if (isAdded) {
            btn.classList.remove("added");
            btn.title = "Guardar para leer después";
            btn.innerHTML = outlinedSvg;
          } else {
            btn.classList.add("added");
            btn.title = "Quitar de leer después";
            btn.innerHTML = filledSvg;
          }
        });
    });
  });
}
