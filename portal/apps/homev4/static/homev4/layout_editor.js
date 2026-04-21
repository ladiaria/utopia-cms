document.addEventListener("DOMContentLoaded", function () {
    var DATA = window.HOMEV4_DATA;
    var dragSrc = null;
    // Tracks whether the current editor state matches what is saved in the DB.
    // Starts true because the editor always loads the saved DB state on first render.
    // markChanged() sets it to false on any edit; saveGrid() sets it back to true on success.
    // Used by the preview button to set the correct banner message (saved vs. unsaved).
    var _gridSaved = true;

    function markChanged() { _gridSaved = false; }

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
            markChanged();
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
        ["principal-articles", "suplemento-articles", "especial-articles"].forEach(function (containerId) {
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
                markChanged();
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
        makeSortable(container, ".newsletter-row[data-newsletter-ref]");
    });

    // ── Fallback notice for PRINCIPAL block ───────────────────────────────────
    function updatePrincipalFallbackNotice() {
        var notice = document.getElementById("principal-fallback-notice");
        if (!notice) return;
        var container = document.getElementById("principal-articles");
        var hasArticles = container && container.querySelectorAll(".article-row[data-article-id]").length > 0;
        notice.style.display = hasArticles ? "none" : "";
    }

    // ── Article remove buttons (for picker-enabled components) ────────────────
    function initRemoveButton(btn, row) {
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            markChanged();
            var headline = row.querySelector(".comp-article-title, .article-title, .section-article-title");
            log("picker", "removed article", {
                id: row.dataset.articleId,
                headline: headline ? headline.textContent.trim() : "?",
            });
            row.remove();
            renumberArticles();
            updatePrincipalFallbackNotice();
        });
    }

    // Wire up remove buttons already present in the rendered HTML (saved articles)
    document.querySelectorAll(".picker-remove").forEach(function (btn) {
        initRemoveButton(btn, btn.closest("[data-article-id], [data-newsletter-ref]"));
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
        markChanged();
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

        var numEl = null;
        if (rowClass === "article-row") {
            numEl = document.createElement("span");
            numEl.className = "article-num";
            numEl.textContent = "?";
        }

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
        if (numEl) row.appendChild(numEl);
        row.appendChild(title);
        row.appendChild(editLink);
        row.appendChild(removeBtn);
        container.appendChild(row);

        // Wire up drag for the new row
        initItemDrag(row, container, itemSelector);

        renumberArticles();
        if (container.id === "principal-articles") updatePrincipalFallbackNotice();
        log("picker", "added article", { id: article.id, headline: article.headline });
    }

    // Returns all article IDs currently present in the editor DOM (across all pickers/zones).
    // Used to exclude already-placed articles from search results without requiring a save.
    function getEditorArticleIds() {
        var ids = [];
        document.querySelectorAll("[data-article-id]").forEach(function (el) {
            var id = parseInt(el.dataset.articleId, 10);
            if (!isNaN(id)) ids.push(id);
        });
        return ids;
    }

    // q: search query string
    // resultsEl: the .picker-results dropdown element
    // articlesContainer: the articles list element to add rows into
    // rowClass / itemSelector: forwarded to addArticleToPicker
    // picker: the .article-picker wrapper (to find the input when clearing)
    function fetchArticles(q, resultsEl, articlesContainer, rowClass, itemSelector, picker, signal) {
        resultsEl.innerHTML = "";
        var loading = document.createElement("div");
        loading.className = "picker-loading";
        loading.innerHTML = '<span class="picker-spinner"></span>';
        resultsEl.appendChild(loading);
        resultsEl.style.display = "block";

        var isNewsletterMode = picker.dataset.mode === "newsletter";
        var baseUrl = isNewsletterMode ? (picker.dataset.searchUrl || DATA.newsletterSearchUrl) : DATA.articleSearchUrl;
        var sep = baseUrl.indexOf("?") >= 0 ? "&" : "?";
        var url = baseUrl + sep + "q=" + encodeURIComponent(q);
        if (!isNewsletterMode) {
            var editorIds = getEditorArticleIds();
            if (editorIds.length) url += "&exclude_ids=" + editorIds.join(",");
        }
        fetch(url, { credentials: "same-origin", signal: signal })
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
                var isNewsletterMode = picker.dataset.mode === "newsletter";
                var replaceMode = picker.dataset.replaceMode === "true";
                var hintEl = replaceMode ? picker.querySelector(".section-replace-hint") : null;
                articles.forEach(function (a) {
                    var row = document.createElement("div");
                    row.className = "picker-result-row";
                    row.textContent = isNewsletterMode ? (a.name + (a.periodicity ? " — " + a.periodicity : "")) : a.headline;
                    row.addEventListener("click", function () {
                        if (isNewsletterMode) {
                            var ref = a.type + ":" + a.slug;
                            var existing = articlesContainer.querySelector("[data-newsletter-ref='" + ref + "']");
                            if (existing) {
                                existing.style.background = "#fffde7";
                                setTimeout(function () { existing.style.background = ""; }, 800);
                            } else {
                                var nlRow = document.createElement("div");
                                nlRow.className = "newsletter-row";
                                nlRow.draggable = true;
                                nlRow.dataset.newsletterRef = ref;
                                var handle = document.createElement("span");
                                handle.className = "drag-handle small-handle";
                                handle.textContent = "⠿";
                                var title = document.createElement("span");
                                title.className = "comp-article-title";
                                title.textContent = a.name;
                                var periodicity = document.createElement("span");
                                periodicity.className = "comp-desc";
                                periodicity.textContent = a.periodicity || "";
                                var removeBtn = document.createElement("button");
                                removeBtn.type = "button";
                                removeBtn.className = "picker-remove";
                                removeBtn.title = "Quitar";
                                removeBtn.textContent = "×";
                                initRemoveButton(removeBtn, nlRow);
                                nlRow.appendChild(handle);
                                nlRow.appendChild(title);
                                nlRow.appendChild(periodicity);
                                nlRow.appendChild(removeBtn);
                                articlesContainer.appendChild(nlRow);
                                initItemDrag(nlRow, articlesContainer, ".newsletter-row[data-newsletter-ref]");
                            }
                            resultsEl.innerHTML = "";
                            resultsEl.style.display = "none";
                            var input = picker.querySelector(".picker-search-input");
                            if (input) input.value = "";
                            return;
                        }
                        if (replaceMode) {
                            var currentCount = articlesContainer.querySelectorAll("[data-article-id]").length;
                            var maxSlots = parseInt(picker.dataset.maxSlots || "2", 10);
                            if (currentCount < maxSlots) {
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
                if (err.name === "AbortError") return;
                log("picker", "search error", err.message);
                resultsEl.innerHTML = "";
                var errEl = document.createElement("div");
                errEl.className = "picker-error";
                errEl.textContent = "Error de conexión, intentá de nuevo";
                resultsEl.appendChild(errEl);
                resultsEl.style.display = "block";
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
            var fetchController = null;
            input.addEventListener("input", function () {
                clearTimeout(timer);
                if (fetchController) { fetchController.abort(); fetchController = null; }
                var q = this.value.trim();
                if (q.length < 2) {
                    resultsEl.innerHTML = "";
                    resultsEl.style.display = "none";
                    return;
                }
                timer = setTimeout(function () {
                    fetchController = new AbortController();
                    fetchArticles(q, resultsEl, articlesContainer, rowClass, itemSelector, picker, fetchController.signal);
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
            var newsletterRows = el.querySelectorAll(".newsletter-row[data-newsletter-ref]");
            if (newsletterRows.length > 0) {
                comp.newsletter_refs = Array.from(newsletterRows).map(function (nr) {
                    return nr.dataset.newsletterRef;
                });
            }
            result.componentes.push(comp);
        });

        return result;
    }

    function saveGrid(onComplete) {
        if (!DATA || !DATA.saveUrl) {
            showStatus("Error: saveUrl no configurado", "error");
            if (onComplete) onComplete();
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
                _gridSaved = true;
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
                document.dispatchEvent(new CustomEvent("homev4:saved"));
            } else {
                showStatus("Error: " + (resp.error || "?"), "error");
                log("save", "error response", resp);
                document.dispatchEvent(new CustomEvent("homev4:saved"));
            }
            if (onComplete) onComplete();
        })
        .catch(function (err) {
            showStatus("Error al guardar: " + err.message, "error");
            log("save", "fetch error", err.message);
            if (onComplete) onComplete();
        });
    }

    document.getElementById("btn-save").addEventListener("click", function () { saveGrid(); });

    // "Vista previa" button: serialize the current editor state, POST it to
    // save_preview_session so Django stores it in the session, then open /?preview=1
    // in a new tab. active_layout reads the session and renders with the editor's
    // current grid_data rather than what is saved in the DB.
    // NOTE: refreshing the preview tab does not reflect changes made in the editor
    // after the preview was opened — the session holds the grid from the last
    // save_preview_session or save_grid call and is not updated until the next click.
    var btnPreview = document.querySelector(".btn-preview");
    if (btnPreview && window.HOMEV4_DATA.previewSessionUrl) {
        btnPreview.addEventListener("click", function () {
            fetch(window.HOMEV4_DATA.previewSessionUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": window.HOMEV4_DATA.csrfToken
                },
                body: JSON.stringify({ grid_data: serializeGrid(), saved: _gridSaved })
            })
            .then(function (r) { return r.json(); })
            .then(function () { window.open("/?preview=1", "_blank"); })
            .catch(function (err) { log("preview", "error saving session", err.message); });
        });
    }

    // Auto-save layout when any Django admin submit button is clicked.
    // Track which button triggered the submit so its name/value is preserved
    // (Django uses _save/_continue/_addanother to decide where to redirect).
    var adminForm = document.querySelector("#content-main form");
    if (adminForm) {
        var _clickedBtn = null;
        adminForm.querySelectorAll("input[type=submit], button[type=submit]").forEach(function (btn) {
            btn.addEventListener("click", function () { _clickedBtn = btn; });
        });
        adminForm.addEventListener("submit", function (e) {
            e.preventDefault();
            var form = this;
            saveGrid(function () {
                if (_clickedBtn && _clickedBtn.name) {
                    var hidden = document.createElement("input");
                    hidden.type = "hidden";
                    hidden.name = _clickedBtn.name;
                    hidden.value = _clickedBtn.value || "1";
                    form.appendChild(hidden);
                }
                form.submit();
            });
        });
    }

    function showStatus(message, type) {
        var el = document.getElementById("save-status");
        if (!el) return;
        el.textContent = message;
        el.className = "save-status " + type;
        el.style.display = "block";
        setTimeout(function () { el.style.display = "none"; }, 4000);
    }
});
