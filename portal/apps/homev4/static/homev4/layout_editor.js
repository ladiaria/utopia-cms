document.addEventListener("DOMContentLoaded", function () {
    var DATA = window.HOMEV4_DATA;
    var dragSrc = null;

    // ── Logging helper ────────────────────────────────────────────────────────
    // Single entry point for all editor events. Category examples: "drag", "toggle", "save", "picker".
    function log(category, message, data) {
        var prefix = "[homev4:" + category + "] " + message;
        if (data !== undefined) {
            console.log(prefix, data);
        } else {
            console.log(prefix);
        }
    }

    // Attach drag-and-drop events to a single item within a container.
    // Called both during initial setup and when new rows are added dynamically (picker).
    function initItemDrag(item, container, itemSelector) {
        item.addEventListener("dragstart", function (e) {
            dragSrc = this;
            e.stopPropagation();
            e.dataTransfer.effectAllowed = "move";
            var self = this;
            setTimeout(function () { self.classList.add("dragging"); }, 0);
        });

        item.addEventListener("dragend", function () {
            this.classList.remove("dragging");
            container.querySelectorAll(itemSelector).forEach(function (el) {
                el.classList.remove("drag-over");
            });
            dragSrc = null;
        });

        item.addEventListener("dragover", function (e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
            container.querySelectorAll(itemSelector).forEach(function (el) {
                el.classList.remove("drag-over");
            });
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

            var items = Array.from(container.querySelectorAll(itemSelector));
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
    }

    // Make a container's direct children sortable via HTML5 drag-and-drop.
    function makeSortable(container, itemSelector) {
        if (!container) return;

        Array.from(container.querySelectorAll(itemSelector)).forEach(function (item) {
            initItemDrag(item, container, itemSelector);
        });

        // Allow dropping into empty space below the last item
        container.addEventListener("dragover", function (e) { e.preventDefault(); });
        container.addEventListener("drop", function (e) {
            e.preventDefault();
            container.querySelectorAll(itemSelector).forEach(function (el) {
                el.classList.remove("drag-over");
            });
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

    // ── Article remove buttons (for picker-enabled components) ────────────────
    function initRemoveButton(btn, row) {
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            var headline = row.querySelector(".comp-article-title, .article-title, .section-article-title");
            log("picker", "removed article", {
                id: row.dataset.articleId,
                headline: headline ? headline.textContent.trim() : "?",
            });
            row.remove();
            renumberArticles();
        });
    }

    // Wire up remove buttons already present in the rendered HTML (saved articles)
    document.querySelectorAll(".picker-remove").forEach(function (btn) {
        initRemoveButton(btn, btn.closest("[data-article-id]"));
    });

    // Highlight section rows when their replace-radio is checked
    document.querySelectorAll(".section-replace-radio input[type='radio']").forEach(function (radio) {
        radio.addEventListener("change", function () {
            var container = this.closest(".section-articles");
            if (!container) return;
            container.querySelectorAll(".section-article-row").forEach(function (r) {
                r.classList.remove("is-marked-for-replace");
            });
            if (this.checked) {
                this.closest(".section-article-row").classList.add("is-marked-for-replace");
            }
        });
    });

    // ── Section add/replace (ÁREAS Y PUBLICACIONES) ──────────────────────────
    // Add a new section row (no × button) and wire up its radio.
    function addArticleToSection(article, container, itemSelector) {
        var row = document.createElement("div");
        row.className = "section-article-row";
        row.draggable = true;
        row.dataset.articleId = article.id;

        var radioLabel = document.createElement("label");
        radioLabel.className = "section-replace-radio";
        radioLabel.title = "Marcar para reemplazar";
        var radio = document.createElement("input");
        radio.type = "radio";
        // Share the same radio group as existing rows in this section
        var existingRadio = container.querySelector("input[type='radio']");
        radio.name = existingRadio ? existingRadio.name : "section-replace-" + container.id;
        radioLabel.appendChild(radio);

        var handle = document.createElement("span");
        handle.className = "drag-handle small-handle";
        handle.textContent = "⠿";

        var title = document.createElement("span");
        title.className = "section-article-title";
        title.textContent = article.headline;

        var editLink = document.createElement("a");
        editLink.className = "article-edit-link";
        editLink.href = "/admin/core/article/" + article.id + "/change/";
        editLink.target = "_blank";
        editLink.title = "Editar artículo";
        editLink.textContent = "✎";

        row.appendChild(radioLabel);
        row.appendChild(handle);
        row.appendChild(title);
        row.appendChild(editLink);
        container.appendChild(row);

        // Wire up radio highlight
        radio.addEventListener("change", function () {
            container.querySelectorAll(".section-article-row").forEach(function (r) {
                r.classList.remove("is-marked-for-replace");
            });
            if (this.checked) this.closest(".section-article-row").classList.add("is-marked-for-replace");
        });

        initItemDrag(row, container, itemSelector);
        log("picker", "added article to section", { id: article.id, headline: article.headline });
    }

    // Replace the radio-marked row with `article`. Returns true on success,
    // false if no row is marked (caller shows the hint).
    function replaceArticleInSection(article, container) {
        var checkedRadio = container.querySelector("input[type='radio']:checked");
        if (!checkedRadio) return false;

        var row = checkedRadio.closest("[data-article-id]");
        if (!row) return false;

        // Duplicate check: article already in another slot
        var existing = container.querySelector("[data-article-id='" + article.id + "']");
        if (existing && existing !== row) {
            existing.style.background = "#fffde7";
            setTimeout(function () { existing.style.background = ""; }, 800);
            log("picker", "duplicate skipped (replace)", { id: article.id });
            return true; // close results but don't replace
        }

        row.dataset.articleId = article.id;
        var titleEl = row.querySelector(".section-article-title");
        if (titleEl) titleEl.textContent = article.headline;
        var editLink = row.querySelector(".article-edit-link");
        if (editLink) editLink.href = "/admin/core/article/" + article.id + "/change/";
        checkedRadio.checked = false;
        row.classList.remove("is-marked-for-replace");

        log("picker", "replaced article in section", { id: article.id, headline: article.headline });
        return true;
    }

    // ── Article picker ────────────────────────────────────────────────────────
    // article: {id, headline}
    // container: the articles list element
    // rowClass: CSS class for the new row (e.g. "comp-article-row", "article-row")
    // itemSelector: drag selector used in initItemDrag (e.g. ".comp-article-row[data-article-id]")
    function addArticleToPicker(article, container, rowClass, itemSelector) {
        // Skip duplicates — briefly highlight the existing row instead
        var existing = container.querySelector("[data-article-id='" + article.id + "']");
        if (existing) {
            existing.style.background = "#fffde7";
            setTimeout(function () { existing.style.background = ""; }, 800);
            log("picker", "duplicate skipped", { id: article.id });
            return;
        }

        var row = document.createElement("div");
        row.className = rowClass;
        row.draggable = true;
        row.dataset.articleId = article.id;

        var handle = document.createElement("span");
        handle.className = "drag-handle small-handle";
        handle.textContent = "⠿";

        var title = document.createElement("span");
        // Use the title class that matches the row class convention
        var titleClassMap = { "article-row": "article-title", "section-article-row": "section-article-title" };
        title.className = titleClassMap[rowClass] || "comp-article-title";
        title.textContent = article.headline;

        var editLink = document.createElement("a");
        editLink.className = "article-edit-link";
        editLink.href = "/admin/core/article/" + article.id + "/change/";
        editLink.target = "_blank";
        editLink.title = "Editar artículo";
        editLink.textContent = "✎";

        var removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "picker-remove";
        removeBtn.title = "Quitar";
        removeBtn.textContent = "×";
        initRemoveButton(removeBtn, row);

        row.appendChild(handle);
        row.appendChild(title);
        row.appendChild(editLink);
        row.appendChild(removeBtn);
        container.appendChild(row);

        // Wire up drag for the new row
        initItemDrag(row, container, itemSelector);

        renumberArticles();
        log("picker", "added article", { id: article.id, headline: article.headline });
    }

    // q: search query string
    // resultsEl: the .picker-results dropdown element
    // articlesContainer: the articles list element to add rows into
    // rowClass / itemSelector: forwarded to addArticleToPicker
    // picker: the .article-picker wrapper (to find the input when clearing)
    function fetchArticles(q, resultsEl, articlesContainer, rowClass, itemSelector, picker) {
        resultsEl.innerHTML = "";
        var loading = document.createElement("div");
        loading.className = "picker-loading";
        loading.textContent = "Buscando\u2026";
        resultsEl.appendChild(loading);
        resultsEl.style.display = "block";

        var url = DATA.articleSearchUrl + "?q=" + encodeURIComponent(q);
        fetch(url, { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (articles) {
                resultsEl.innerHTML = "";
                if (articles.length === 0) {
                    var empty = document.createElement("div");
                    empty.className = "picker-no-results";
                    empty.textContent = "Sin resultados";
                    resultsEl.appendChild(empty);
                    resultsEl.style.display = "block";
                    return;
                }
                var replaceMode = picker.dataset.replaceMode === "true";
                var hintEl = replaceMode ? picker.querySelector(".section-replace-hint") : null;
                articles.forEach(function (a) {
                    var row = document.createElement("div");
                    row.className = "picker-result-row";
                    row.textContent = a.headline;
                    row.addEventListener("click", function () {
                        if (replaceMode) {
                            var currentCount = articlesContainer.querySelectorAll("[data-article-id]").length;
                            if (currentCount < 2) {
                                // Free slot: just add
                                addArticleToSection(a, articlesContainer, itemSelector);
                            } else {
                                // Full: require a marked radio
                                var ok = replaceArticleInSection(a, articlesContainer);
                                if (!ok) {
                                    if (hintEl) {
                                        hintEl.style.display = "block";
                                        setTimeout(function () { hintEl.style.display = "none"; }, 3000);
                                    }
                                    return; // keep results open so user can mark a row then retry
                                }
                            }
                        } else {
                            addArticleToPicker(a, articlesContainer, rowClass, itemSelector);
                        }
                        resultsEl.innerHTML = "";
                        resultsEl.style.display = "none";
                        var input = picker.querySelector(".picker-search-input");
                        if (input) input.value = "";
                    });
                    resultsEl.appendChild(row);
                });
                resultsEl.style.display = "block";
            })
            .catch(function (err) {
                log("picker", "search error", err.message);
            });
    }

    // Initialize all .article-picker elements on the page.
    // Required data attributes on the .article-picker element:
    //   data-target        — id of the articles container to add rows into
    //   data-row-class     — CSS class for created rows (e.g. "comp-article-row")
    //   data-item-selector — drag selector within the container (e.g. ".comp-article-row[data-article-id]")
    function initPickers() {
        document.querySelectorAll(".article-picker").forEach(function (picker) {
            var targetId = picker.dataset.target;
            var rowClass = picker.dataset.rowClass || "comp-article-row";
            var itemSelector = picker.dataset.itemSelector || ("." + rowClass + "[data-article-id]");
            var input = picker.querySelector(".picker-search-input");
            var resultsEl = picker.querySelector(".picker-results");
            var articlesContainer = targetId ? document.getElementById(targetId) : null;
            if (!input || !resultsEl || !articlesContainer) return;

            var timer = null;
            input.addEventListener("input", function () {
                clearTimeout(timer);
                var q = this.value.trim();
                if (q.length < 2) {
                    resultsEl.innerHTML = "";
                    resultsEl.style.display = "none";
                    return;
                }
                timer = setTimeout(function () {
                    fetchArticles(q, resultsEl, articlesContainer, rowClass, itemSelector, picker);
                }, 300);
            });

            input.addEventListener("keydown", function (e) {
                var rows = Array.from(resultsEl.querySelectorAll(".picker-result-row"));
                if (!rows.length) return;
                var focused = resultsEl.querySelector(".picker-result-row.picker-focused");
                var idx = focused ? rows.indexOf(focused) : -1;

                if (e.key === "ArrowDown") {
                    e.preventDefault();
                    var next = rows[idx + 1] || rows[0];
                    rows.forEach(function (r) { r.classList.remove("picker-focused"); });
                    next.classList.add("picker-focused");
                    next.scrollIntoView({ block: "nearest" });
                } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    var prev = rows[idx - 1] || rows[rows.length - 1];
                    rows.forEach(function (r) { r.classList.remove("picker-focused"); });
                    prev.classList.add("picker-focused");
                    prev.scrollIntoView({ block: "nearest" });
                } else if (e.key === "Enter") {
                    e.preventDefault();
                    if (focused) focused.click();
                } else if (e.key === "Escape") {
                    resultsEl.innerHTML = "";
                    resultsEl.style.display = "none";
                }
            });

            // Close results when clicking outside this picker
            document.addEventListener("click", function (e) {
                if (!picker.contains(e.target)) {
                    resultsEl.innerHTML = "";
                    resultsEl.style.display = "none";
                }
            });
        });
    }
    initPickers();

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
