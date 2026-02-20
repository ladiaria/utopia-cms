document.addEventListener("DOMContentLoaded", function () {
    var DATA = window.HOMEV4_DATA;
    var dragSrc = null;

    // Make a container's direct children sortable via HTML5 drag-and-drop
    function makeSortable(container, itemSelector) {
        if (!container) return;

        function getItems() {
            return Array.from(container.querySelectorAll(itemSelector));
        }

        function clearOver() {
            getItems().forEach(function (el) { el.classList.remove("drag-over"); });
        }

        getItems().forEach(function (item) {
            item.addEventListener("dragstart", function (e) {
                dragSrc = this;
                e.dataTransfer.effectAllowed = "move";
                var self = this;
                setTimeout(function () { self.classList.add("dragging"); }, 0);
            });

            item.addEventListener("dragend", function () {
                this.classList.remove("dragging");
                clearOver();
                dragSrc = null;
            });

            item.addEventListener("dragover", function (e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                clearOver();
                this.classList.add("drag-over");
            });

            item.addEventListener("dragleave", function (e) {
                if (!this.contains(e.relatedTarget)) {
                    this.classList.remove("drag-over");
                }
            });

            item.addEventListener("drop", function (e) {
                e.preventDefault();
                e.stopPropagation();
                this.classList.remove("drag-over");
                if (!dragSrc || dragSrc === this) return;

                var items = getItems();
                var srcIdx = items.indexOf(dragSrc);
                var destIdx = items.indexOf(this);
                if (srcIdx === -1 || destIdx === -1) return;

                if (srcIdx < destIdx) {
                    container.insertBefore(dragSrc, this.nextSibling);
                } else {
                    container.insertBefore(dragSrc, this);
                }

                renumberArticles();
            });
        });

        // Allow dropping into empty space below the last item
        container.addEventListener("dragover", function (e) { e.preventDefault(); });
        container.addEventListener("drop", function (e) {
            e.preventDefault();
            clearOver();
            if (dragSrc && dragSrc.parentNode === container) {
                container.appendChild(dragSrc);
                renumberArticles();
            }
        });
    }

    // Update the 1-7 numbers shown next to article titles after reorder
    function renumberArticles() {
        var inicioContainer = document.getElementById("inicio-articles");
        if (!inicioContainer) return;
        inicioContainer.querySelectorAll(".article-num").forEach(function (el, i) {
            el.textContent = i + 1;
        });
    }

    // Init: article sorting within INICIO
    makeSortable(document.getElementById("inicio-articles"), ".article-row[data-article-id]");

    // Init: article sorting within each section block (only within its own container)
    document.querySelectorAll("#sections-list .section-sortable").forEach(function (container) {
        makeSortable(container, ".section-article-row[data-article-id]");
    });

    // Build the JSON payload to save
    function serializeGrid() {
        var result = {
            inicio: { article_ids: [] },
            sections: [],
            componentes: {}
        };

        // INICIO article order
        var inicioContainer = document.getElementById("inicio-articles");
        if (inicioContainer) {
            inicioContainer.querySelectorAll(".article-row[data-article-id]").forEach(function (el) {
                result.inicio.article_ids.push(parseInt(el.dataset.articleId, 10));
            });
        }

        // Sections with their article order
        var sectionsList = document.getElementById("sections-list");
        if (sectionsList) {
            sectionsList.querySelectorAll(".block-area[data-section-id]").forEach(function (el) {
                var sec = {
                    type: el.dataset.sectionType,
                    id: parseInt(el.dataset.sectionId, 10),
                    name: el.dataset.sectionName
                };
                var articleRows = el.querySelectorAll(".section-article-row[data-article-id]");
                if (articleRows.length > 0) {
                    sec.article_ids = Array.from(articleRows).map(function (ar) {
                        return parseInt(ar.dataset.articleId, 10);
                    });
                }
                result.sections.push(sec);
            });
        }

        // Componentes active states
        document.querySelectorAll(".componente-item[data-comp-key]").forEach(function (el) {
            var key = el.dataset.compKey;
            var active = el.querySelector(".comp-active").checked;
            result.componentes[key] = { active: active };
        });

        return result;
    }

    function saveGrid() {
        if (!DATA || !DATA.saveUrl) {
            showStatus("Error: saveUrl no configurado", "error");
            return;
        }
        var payload = serializeGrid();
        console.log("[homev4] saving:", JSON.stringify(payload).slice(0, 300));
        fetch(DATA.saveUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": DATA.csrfToken
            },
            body: JSON.stringify({ grid_data: payload })
        })
        .then(function (r) {
            if (!r.ok) {
                throw new Error("HTTP " + r.status + " " + r.statusText);
            }
            return r.json();
        })
        .then(function (resp) {
            if (resp.status === "ok") {
                showStatus(
                    "Guardado — INICIO: " + resp.saved_inicio + " arts, secciones: " + resp.saved_sections,
                    "success"
                );
            } else {
                showStatus("Error: " + (resp.error || "?"), "error");
                console.error("[homev4] save error response:", resp);
            }
        })
        .catch(function (err) {
            showStatus("Error al guardar: " + err.message, "error");
            console.error("[homev4] saveGrid error:", err);
        });
    }

    document.getElementById("btn-save").addEventListener("click", saveGrid);

    function showStatus(message, type) {
        var el = document.getElementById("save-status");
        if (!el) return;
        el.textContent = message;
        el.className = "save-status " + type;
        el.style.display = "block";
        setTimeout(function () { el.style.display = "none"; }, 4000);
    }
});
