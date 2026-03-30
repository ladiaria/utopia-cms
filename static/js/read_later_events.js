function read_later_events(articleContentTypeId, container) {
  const scope = container ? container : document;
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
          } else {
            btn.classList.add("added");
            btn.title = "Quitar de leer después";
          }
        });
    });
  });
}
