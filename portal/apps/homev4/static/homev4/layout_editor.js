document.addEventListener("DOMContentLoaded", function () {
    var DATA = window.HOMEV4_DATA;
    var dragSrc = null;

    // ── Logging helper ────────────────────────────────────────────────────────
    // Single entry point for all editor events. Category examples: "drag", "toggle", "save".
    function log(category, message, data) {
        var prefix = "[homev4:" + category + "] " + message;
        if (data !== undefined) {
            console.log(prefix, data);
        } else {
            console.log(prefix);
        }
    }

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
                e.stopPropagation();  // prevent parent draggable from stealing the drag
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

                var label = dragSrc.querySelector(".article-title, .section-article-title, .comp-name, .comp-article-title");
                log("drag", "reordered", {
                    item: label ? label.textContent.trim() : dragSrc.dataset.articleId || dragSrc.dataset.compKey,
                    from: srcIdx + 1,
                    to: destIdx + 1,
                });

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

    // Renumber position indicators after reorder
    function renumberArticles() {
        ["principal-articles", "suplemento-articles"].forEach(function (containerId) {
            var container = document.getElementById(containerId);
            if (!container) return;
            container.querySelectorAll(".article-num").forEach(function (el, i) {
                el.textContent = i + 1;
            });
        });
    }

    // Single function: toggle .is-inactive on the closest toggleable container
    var TOGGLE_CONTAINER = ".editor-block, .componente-item";
    var TOGGLE_CHECKBOXES = ".block-active, .section-active, .comp-active";

    function applyActiveState(checkbox) {
        var block = checkbox.closest(TOGGLE_CONTAINER);
        if (!block) return;
        block.classList.toggle("is-inactive", !checkbox.checked);
    }

    function initActiveToggles() {
        document.querySelectorAll(TOGGLE_CHECKBOXES).forEach(function (cb) {
            applyActiveState(cb);
            cb.addEventListener("change", function () {
                applyActiveState(this);
                var block = this.closest(TOGGLE_CONTAINER);
                var nameEl = block && block.querySelector(".block-badge, .comp-name");
                log("toggle", (this.checked ? "activated" : "deactivated"), {
                    block: nameEl ? nameEl.textContent.trim() : (this.dataset.block || "?"),
                });
            });
        });
    }
    initActiveToggles();

    // Init: article sorting within PRINCIPAL
    makeSortable(document.getElementById("principal-articles"), ".article-row[data-article-id]");

    // Init: article sorting within SUPLEMENTO
    makeSortable(document.getElementById("suplemento-articles"), ".article-row[data-article-id]");

    // Init: article sorting within each section block (only within its own container)
    document.querySelectorAll("#sections-list .section-sortable").forEach(function (container) {
        makeSortable(container, ".section-article-row[data-article-id]");
    });

    // Init: component reordering
    makeSortable(document.getElementById("componentes-list"), ".componente-item[data-comp-key]");

    // Init: article sorting within each component
    document.querySelectorAll(".comp-articles").forEach(function (container) {
        makeSortable(container, ".comp-article-row[data-article-id]");
    });

    // Build the JSON payload to save
    function serializeGrid() {
        var result = {
            principal:  { active: true, article_ids: [] },
            suplemento: { active: true, article_ids: [] },
            especial:   { active: true, article_ids: [] },
            sections: [],
            componentes: []
        };

        function readBlockActive(blockName) {
            var cb = document.querySelector(".block-active[data-block='" + blockName + "']");
            return cb ? cb.checked : true;
        }

        // PRINCIPAL
        result.principal.active = readBlockActive("principal");
        var principalContainer = document.getElementById("principal-articles");
        if (principalContainer) {
            principalContainer.querySelectorAll(".article-row[data-article-id]").forEach(function (el) {
                result.principal.article_ids.push(parseInt(el.dataset.articleId, 10));
            });
        }

        // SUPLEMENTO
        result.suplemento.active = readBlockActive("suplemento");
        var suplementoContainer = document.getElementById("suplemento-articles");
        if (suplementoContainer) {
            suplementoContainer.querySelectorAll(".article-row[data-article-id]").forEach(function (el) {
                result.suplemento.article_ids.push(parseInt(el.dataset.articleId, 10));
            });
        }

        // ESPECIAL
        result.especial.active = readBlockActive("especial");
        var especialContainer = document.getElementById("especial-articles");
        if (especialContainer) {
            especialContainer.querySelectorAll(".article-row[data-article-id]").forEach(function (el) {
                result.especial.article_ids.push(parseInt(el.dataset.articleId, 10));
            });
        }

        // Sections with their article order, active state, slug and row
        var sectionsList = document.getElementById("sections-list");
        if (sectionsList) {
            sectionsList.querySelectorAll(".block-area").forEach(function (el) {
                var activeCheckbox = el.querySelector(".section-active");
                var sec = {
                    type: el.dataset.sectionType || "section",
                    slug: el.dataset.sectionSlug || null,
                    name: el.dataset.sectionName || "",
                    row: parseInt(el.dataset.sectionRow, 10) || 1,
                    active: activeCheckbox ? activeCheckbox.checked : true,
                    article_ids: []
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

        // Componentes: save as ordered list to preserve custom drag order
        result.componentes = [];
        document.querySelectorAll(".componente-item[data-comp-key]").forEach(function (el) {
            var comp = {
                key: el.dataset.compKey,
                active: el.querySelector(".comp-active").checked
            };
            var articleRows = el.querySelectorAll(".comp-article-row[data-article-id]");
            if (articleRows.length > 0) {
                comp.article_ids = Array.from(articleRows).map(function (ar) {
                    return parseInt(ar.dataset.articleId, 10);
                });
            }
            result.componentes.push(comp);
        });

        return result;
    }

    function saveGrid() {
        if (!DATA || !DATA.saveUrl) {
            showStatus("Error: saveUrl no configurado", "error");
            return;
        }
        var payload = serializeGrid();
        log("save", "sending", {
            principal: payload.principal.article_ids.length,
            suplemento: payload.suplemento.article_ids.length,
            sections: payload.sections.length,
            componentes: payload.componentes.length,
        });
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
                var labels = (DATA && DATA.componentLabels) || {};
                var activeLabels = (resp.componentes_active || []).map(function (key) {
                    return labels[key] || key;
                });
                var compsStr = activeLabels.length
                    ? activeLabels.join(", ")
                    : "ninguno";
                var msg = "Guardado"
                    + " · portada: " + resp.principal + " arts"
                    + " · áreas: " + resp.sections_active + "/" + resp.sections_total
                    + " · activos: " + compsStr;
                showStatus(msg, "success");
                log("save", "ok", {
                    principal: resp.principal,
                    suplemento: resp.suplemento,
                    sections: resp.sections_active + "/" + resp.sections_total,
                    componentes_active: compsStr,
                });
            } else {
                showStatus("Error: " + (resp.error || "?"), "error");
                log("save", "error response", resp);
            }
        })
        .catch(function (err) {
            showStatus("Error al guardar: " + err.message, "error");
            log("save", "fetch error", err.message);
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
