(function () {
  "use strict";

  function qsa(selector, root) {
    return Array.from((root || document).querySelectorAll(selector));
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function onAll(selector, eventName, handler, root) {
    qsa(selector, root).forEach(function (node) {
      node.addEventListener(eventName, handler);
    });
  }

  function fadeOut(element, duration) {
    const animationDuration = duration || 600;
    element.style.transition = "opacity " + animationDuration + "ms ease";
    element.style.opacity = "1";
    requestAnimationFrame(function () {
      element.style.opacity = "0";
    });
    window.setTimeout(function () {
      element.style.display = "none";
      element.style.transition = "";
    }, animationDuration);
  }

  function slideToggle(element, duration) {
    const animationDuration = duration || 300;
    const isHidden = window.getComputedStyle(element).display === "none";
    element.style.overflow = "hidden";
    element.style.transition = "max-height " + animationDuration + "ms ease";

    if (isHidden) {
      element.style.display = "block";
      const targetHeight = element.scrollHeight;
      element.style.maxHeight = "0px";
      requestAnimationFrame(function () {
        element.style.maxHeight = targetHeight + "px";
      });
      window.setTimeout(function () {
        element.style.maxHeight = "";
        element.style.transition = "";
        element.style.overflow = "";
      }, animationDuration);
      return;
    }

    element.style.maxHeight = element.scrollHeight + "px";
    requestAnimationFrame(function () {
      element.style.maxHeight = "0px";
    });
    window.setTimeout(function () {
      element.style.display = "none";
      element.style.maxHeight = "";
      element.style.transition = "";
      element.style.overflow = "";
    }, animationDuration);
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      const existingScript = document.querySelector('script[src="' + src + '"]');
      if (existingScript) {
        if (existingScript.dataset.loaded === "true") {
          resolve();
          return;
        }
        existingScript.addEventListener("load", resolve, { once: true });
        existingScript.addEventListener("error", reject, { once: true });
        return;
      }

      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.addEventListener(
        "load",
        function () {
          script.dataset.loaded = "true";
          resolve();
        },
        { once: true }
      );
      script.addEventListener("error", reject, { once: true });
      document.head.appendChild(script);
    });
  }

  function dismissPaywallSnackbar() {
    qsa(".js-ld-snackbar").forEach(function (snackbar) {
      snackbar.classList.remove("ld-snackbar--active");
    });

    window.setTimeout(function () {
      qsa(".js-ld-snackbar").forEach(function (snackbar) {
        snackbar.remove();
      });
    }, 1000); // Fallback
  }

  // Reflect the share sheet open state on the mobile nav share icon so it shows
  // its active (black) state while the sheet is open.
  function setMobileShareActive(isActive) {
    qsa(".js-nav-menu__share").forEach(function (btn) {
      btn.classList.toggle("active", isActive);
    });
  }

  function bindMobileShare() {
    onAll(".js-nav-menu__share", "click", function (event) {
      const share = qs("#article-share-full");
      if (share) {
        share.classList.toggle("active");
        setMobileShareActive(share.classList.contains("active"));
      }
      event.preventDefault();
    });

    onAll("#article-share-full .modal-close", "click", function () {
      const share = qs("#article-share-full");
      if (share) {
        share.classList.remove("active");
      }
      setMobileShareActive(false);
    });
  }

  function onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
      return;
    }
    callback();
  }

  onReady(function () {
    let lockedScrollTop = 0;

    function setDocumentScrollLocked(locked) {
      if (locked) {
        lockedScrollTop = window.scrollY || window.pageYOffset || 0;
        document.body.style.position = "fixed";
        document.body.style.top = "-" + lockedScrollTop + "px";
        document.body.style.left = "0";
        document.body.style.right = "0";
        document.body.style.width = "100%";
        return;
      }

      document.body.style.position = "";
      document.body.style.top = "";
      document.body.style.left = "";
      document.body.style.right = "";
      document.body.style.width = "";
      window.scrollTo({ top: lockedScrollTop, behavior: "instant" });
    }

    function setMainMenuState(isOpen) {
      const body = document.body;
      qsa(".js-ld-main-menu").forEach(function (menu) {
        menu.classList.toggle("active", isOpen);
      });
      body.classList.toggle("main-menu-open", isOpen);
      if (!isOpen) {
        body.classList.remove("mobile-search-open");
        qsa(".header-search.header-search--open").forEach(function (el) {
          el.classList.remove("header-search--open");
          const toggle = qs(".header-search__toggle", el);
          if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Abrir buscador");
          }
        });
      }
      setDocumentScrollLocked(isOpen);
    }

    if (window.M && window.M.Modal) {
      window.M.Modal.init(qsa(".modal"), {
        dismissible: true, // Modal can be dismissed by clicking outside of the modal
        opacity: 0.5, // Opacity of modal background
        inDuration: 300, // Transition in duration
        outDuration: 200, // Transition out duration
        startingTop: "4%", // Starting top style attribute
        endingTop: "10%" // Ending top style attribute
      });
    }

    onAll(".js-ld-main-menu-toggle", "click", function (event) {
      const menuIsOpen = document.body.classList.contains("main-menu-open");
      setMainMenuState(!menuIsOpen);
      event.preventDefault();
    });

    // Header search toggle — each toggle operates on its own .header-search via closest()
    const headerSearchToggles = qsa(".header-search__toggle");
    const mobileBreakpoint = window.matchMedia("(max-width: 992px)");

    function setSearchOpen(headerSearch, isOpen) {
      headerSearch.classList.toggle("header-search--open", isOpen);
      const toggle = qs(".header-search__toggle", headerSearch);
      if (toggle) {
        toggle.setAttribute("aria-expanded", String(isOpen));
        toggle.setAttribute("aria-label", isOpen ? "Cerrar buscador" : "Abrir buscador");
      }
    }

    if (headerSearchToggles.length) {
      headerSearchToggles.forEach(function (toggle) {
        toggle.addEventListener("click", function (event) {
          event.preventDefault();
          if (mobileBreakpoint.matches) {
            const searchIsOpen = document.body.classList.contains("mobile-search-open");
            if (searchIsOpen) {
              document.body.classList.remove("mobile-search-open");
              toggle.setAttribute("aria-label", "Abrir buscador");
            } else {
              document.body.classList.add("mobile-search-open");
              toggle.setAttribute("aria-label", "Cerrar buscador");
              if (!document.body.classList.contains("main-menu-open")) {
                setMainMenuState(true);
              }
              const mobileInput = qs(".mobile-header-search__input");
              if (mobileInput) mobileInput.focus();
            }
          } else {
            const headerSearch = toggle.closest(".header-search");
            if (!headerSearch) return;
            const isOpen = !headerSearch.classList.contains("header-search--open");
            setSearchOpen(headerSearch, isOpen);
            if (isOpen) {
              const input = qs(".header-search__input", headerSearch);
              if (input) input.focus();
            }
          }
        });
      });

      document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        if (mobileBreakpoint.matches) return;
        const openSearch = qs(".header-search.header-search--open");
        if (openSearch) {
          setSearchOpen(openSearch, false);
          const toggle = qs(".header-search__toggle", openSearch);
          if (toggle) toggle.focus();
        }
      });
    }

    document.addEventListener("keyup", function (event) {
      if (event.key !== "Escape" && event.keyCode !== 27) {
        return;
      }
      setMainMenuState(false);
      qsa(".ld-modal").forEach(function (modal) {
        modal.classList.remove("active");
      });
      document.querySelectorAll("[data-activates]").forEach(function (btn) {
        const target = document.getElementById(btn.dataset.activates);
        if (target) target.classList.remove("is-open");
        btn.setAttribute("aria-expanded", "false");
      });
    });

    onAll(".alert-close", "click", function () {
      qsa(".alert-box").forEach(function (alertBox) {
        fadeOut(alertBox, 600);
      });
    });

    // device detection
    const isMobile =
      /(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|ipad|iris|kindle|Android|Silk|lge |maemo|midp|mmp|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino/i.test(
        navigator.userAgent
      ) ||
      /1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(
        navigator.userAgent.substr(0, 4)
      );

    if (window.M && window.M.FormSelect) {
      window.M.FormSelect.init(qsa("select"));
    }

    onAll(".js-close-ld-snackbar", "click", function () {
      dismissPaywallSnackbar();
    });

    onAll(".js-modal-trigger", "click", function () {
      const modalID = this.dataset.trigger;
      if (!modalID) {
        return;
      }
      const modal = qs(modalID);
      if (modal) {
        modal.classList.add("active");
      }
    });

    onAll(".js-modal-close", "click", function () {
      qsa(".ld-modal").forEach(function (modal) {
        modal.classList.remove("active");
      });
    });

    document.body.addEventListener("click", function (event) {
      const dismissButton = event.target.closest(".js-dismiss-message");
      if (!dismissButton) {
        return;
      }
      const parent = dismissButton.parentElement;
      if (parent) {
        parent.remove();
      }
    });

    bindMobileShare();

    const headerElement = qs("header");
    if (headerElement) {
      const updateHeaderStickyState = function () {
        headerElement.classList.toggle("sticky", window.scrollY > 0);
      };

      window.addEventListener("scroll", updateHeaderStickyState, { passive: true });
      updateHeaderStickyState();
    }

    // Article breadcrumb (mobile): hides when scrolling down and reappears pinned
    // below the header when scrolling up. The CSS only applies on mobile
    // (body.article-detail); here we set the offset = header height and toggle the
    // class based on the scroll direction.
    const mobileBreadcrumb = qs(".article-mobile-breadcrumb");
    if (mobileBreadcrumb && headerElement) {
      let lastBreadcrumbScrollY = window.scrollY || 0;
      const breadcrumbThreshold = 5; // ignore micro-scrolls

      const setBreadcrumbOffset = function () {
        // offsetHeight rounds up the header's 0.5px border-bottom (64.5 -> 65),
        // leaving an extra pixel; flooring the rect gives the real height (64).
        const headerHeight = Math.floor(
          headerElement.getBoundingClientRect().height
        );
        mobileBreadcrumb.style.setProperty(
          "--breadcrumb-offset",
          headerHeight + "px"
        );
      };

      const updateBreadcrumbReveal = function () {
        const currentY = window.scrollY || 0;
        if (currentY <= 0) {
          mobileBreadcrumb.classList.remove("is-hidden");
        } else if (currentY > lastBreadcrumbScrollY + breadcrumbThreshold) {
          mobileBreadcrumb.classList.add("is-hidden");
        } else if (currentY < lastBreadcrumbScrollY - breadcrumbThreshold) {
          mobileBreadcrumb.classList.remove("is-hidden");
        }
        lastBreadcrumbScrollY = currentY;
      };

      setBreadcrumbOffset();
      window.addEventListener("scroll", updateBreadcrumbReveal, { passive: true });
      window.addEventListener("resize", setBreadcrumbOffset, { passive: true });
    }

    function initCategoryNavbarGradients() {
      const categoryNavbars = qsa("nav.navbar");
      if (categoryNavbars.length === 0) {
        return;
      }

      const epsilon = 1; // Pixel tolerance for sub-pixel rounding differences.
      const updateNavbarGradientState = function (navbar) {
        const list = qs("ul", navbar);
        if (!list) {
          return;
        }

        const hasOverflow = list.scrollWidth - list.clientWidth > epsilon;
        if (!hasOverflow) {
          navbar.classList.remove("with-left-gradient");
          navbar.classList.remove("with-right-gradient");
          return;
        }

        const isAtLeftEdge = list.scrollLeft <= epsilon;
        const isAtRightEdge =
          list.scrollLeft + list.clientWidth >= list.scrollWidth - epsilon;

        navbar.classList.toggle("with-left-gradient", !isAtLeftEdge);
        navbar.classList.toggle("with-right-gradient", !isAtRightEdge);
      };

      const updateAllNavbars = function () {
        categoryNavbars.forEach(function (navbar) {
          updateNavbarGradientState(navbar);
        });
      };

      categoryNavbars.forEach(function (navbar) {
        const list = qs("ul", navbar);
        if (!list) {
          return;
        }
        list.addEventListener(
          "scroll",
          function () {
            updateNavbarGradientState(navbar);
          },
          { passive: true }
        );
      });

      window.addEventListener("resize", updateAllNavbars);
      window.addEventListener("orientationchange", updateAllNavbars);
      window.addEventListener("load", updateAllNavbars);
      updateAllNavbars();
    }

    initCategoryNavbarGradients();

    function loadComments() {
      const coralStream = qs("#coral_talk_stream");
      if (!coralStream) {
        return;
      }
      const commentsContainer = qs("#comentarios");
      if (commentsContainer) {
        commentsContainer.classList.remove("closed");
      }

      const talkURL = coralStream.getAttribute("data-talk-url");
      if (!talkURL) {
        return;
      }

      loadScript(talkURL + "assets/js/embed.js")
        .then(function () {
          const coralOptions = {
            id: "coral_talk_stream",
            autoRender: true,
            rootURL: talkURL,
            storyID: coralStream.getAttribute("data-article-id"),
            storyURL: coralStream.getAttribute("data-article-url"),
            accessToken: coralStream.getAttribute("data-talk-auth-token"),
            customScrollContainer: qs("#comentarios"),
            events: function (events) {
              events.on("loginPrompt", function () {
                const loginURL = coralStream.getAttribute("data-login-url");
                if (loginURL) {
                  location.href = loginURL;
                }
              });
            }
          };

          if (coralOptions.accessToken) {
            coralOptions.bodyClassName = "logged-in";
          }

          if (window.Coral && typeof window.Coral.createStreamEmbed === "function") {
            window.Coral.createStreamEmbed(coralOptions);
          }

          qsa(".talk-login").forEach(function (node) {
            node.classList.add("active");
          });
        })
        .catch(function () { });
    }

    function updateCommentsBorderState() {
      const commentsContainer = qs("#comentarios");
      if (!commentsContainer) {
        return;
      }

      const upperContent = qs(".upper-content", commentsContainer);
      if (!upperContent) {
        return;
      }

      upperContent.classList.toggle(
        "with-border-bottom",
        commentsContainer.scrollTop > 0
      );
    }

    onAll(".btn-comments, .action-bar-comment-btn", "click", function () {
      loadComments();
    });

    onAll(".toggle-comments", "click", function () {
      const commentsContainer = qs("#comentarios");
      if (commentsContainer) {
        commentsContainer.classList.add("closed");
      }
    });

    // Close the comments panel when clicking outside of it
    document.addEventListener("click", function (event) {
      const commentsContainer = qs("#comentarios");
      if (!commentsContainer || commentsContainer.classList.contains("closed")) {
        return;
      }
      // Ignore clicks inside the panel or on the buttons that open it
      if (
        event.target.closest("#comentarios") ||
        event.target.closest(".btn-comments") ||
        event.target.closest(".action-bar-comment-btn")
      ) {
        return;
      }
      commentsContainer.classList.add("closed");
    });

    // Load comments if coming from AMP version
    if (window.location.hash === "#comentarios") {
      loadComments();
    }

    // Fetch comment count asynchronously via Django proxy endpoint
    (function fetchCommentCount() {
      const coralStream = qs("#coral_talk_stream");
      if (!coralStream) return;
      const articleId = coralStream.getAttribute("data-article-id");
      if (!articleId) return;

      fetch("/articulo/" + articleId + "/comment-count/")
        .then(function (r) { return r.json(); })
        .then(function (data) {
          const count = data && data.count;
          if (!count) return;
          const btnComments = qs(".btn-comments");
          if (btnComments) {
            btnComments.querySelector("p").innerHTML =
              "<span>" + count + "</span> <span>comentario" + (count !== 1 ? "s" : "") + "</span>";
          }
          const upperP = qs("#comentarios .upper-content p");
          if (upperP) {
            upperP.textContent = "Comentarios (" + count + ")";
          }
        })
        .catch(function () {});
    })();

    const commentsContainer = qs("#comentarios");
    if (commentsContainer) {
      commentsContainer.addEventListener(
        "scroll",
        function () {
          updateCommentsBorderState();
        },
        { passive: true }
      );
      updateCommentsBorderState();
    }

    onAll(".ld-audio__audio", "play", function (event) {
      if (qsa(".ld-audio__overlay").length > 0) {
        this.pause();
        event.preventDefault();
        qsa(".ld-audio__overlay").forEach(function (overlay) {
          overlay.classList.add("active");
        });
        console.log("Audio forbidden.");
      }
    });

    onAll(".ld-audio__overlay-close-btn", "click", function () {
      qsa(".ld-audio__overlay").forEach(function (overlay) {
        overlay.classList.remove("active");
      });
    });

    // toggle password visibility
    onAll(".toggle-password", "click", function () {
      this.classList.toggle("visibility-on");
      const id = this.dataset.toggle;
      if (!id) {
        return;
      }
      const input = qs(id);
      if (!input) {
        return;
      }
      if (input.getAttribute("type") === "password") {
        input.setAttribute("type", "text");
      } else {
        input.setAttribute("type", "password");
      }
    });

    // faq component behavior
    qsa(".ld-collapsible").forEach(function (collapsible) {
      collapsible.classList.add("js");
    });
    onAll(".ld-collapsible > li > .collapsible-header", "click", function () {
      const parent = this.closest("li");
      if (parent) {
        parent.classList.toggle("active");
      }
      const body = this.nextElementSibling;
      if (body && body.classList.contains("collapsible-body")) {
        slideToggle(body);
      }
    });

    // generic dropdown toggle (data-activates="<id>")
    function positionNavDropdown(btn, dropdown) {
      const rect = btn.getBoundingClientRect();
      dropdown.style.left = "";
      dropdown.style.right = "";
      if (btn.dataset.dropdownPosition === "right") {
        const offset = 8;
        const dropWidth = dropdown.offsetWidth;
        dropdown.style.top = rect.top + "px";
        if (rect.right + offset + dropWidth > window.innerWidth - 8) {
          dropdown.style.right = (window.innerWidth - rect.left + offset) + "px";
          dropdown.style.left = "auto";
        } else {
          dropdown.style.left = (rect.right + offset) + "px";
          dropdown.style.right = "auto";
        }
      } else {
        const offset = window.innerWidth <= 992 ? 5 : 15;
        dropdown.style.top = (rect.bottom + offset) + "px";
        const dropWidth = dropdown.offsetWidth;
        if (rect.left + dropWidth > window.innerWidth - 8) {
          dropdown.style.right = (window.innerWidth - rect.right) + "px";
          dropdown.style.left = "auto";
        } else {
          dropdown.style.left = rect.left + "px";
          dropdown.style.right = "auto";
        }
      }
    }

    function closeNavDropdown(dropdown, btn) {
      dropdown.classList.remove("is-open");
      if (btn) btn.setAttribute("aria-expanded", "false");
    }

    window.addEventListener("scroll", function () {
      document.querySelectorAll(".dropdown-content.is-open").forEach(function (dropdown) {
        const btn = document.querySelector("[data-activates='" + dropdown.id + "']");
        closeNavDropdown(dropdown, btn);
      });
    }, { passive: true });

    onAll("[data-activates]", "click", function (event) {
      const btn = this;
      const target = document.getElementById(btn.dataset.activates);
      if (!target) return;
      const isOpen = target.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", String(isOpen));
      if (isOpen) {
        positionNavDropdown(btn, target);
      }
      event.stopPropagation();
    });

    document.addEventListener("click", function (event) {
      document.querySelectorAll("[data-activates]").forEach(function (btn) {
        const target = document.getElementById(btn.dataset.activates);
        if (!target || !target.classList.contains("is-open")) return;
        if (!target.contains(event.target)) {
          closeNavDropdown(target, btn);
        }
      });
    });

    // Navbar scroll: show overflow arrows when items don't fit (desktop only)
    qsa(".scrollable-navbar__scrollable").forEach(function (wrapper) {
      const list = qs("ul", wrapper);
      if (!list) return;

      list.addEventListener("scroll", function () {
        document.querySelectorAll(".dropdown-content.is-open").forEach(function (dropdown) {
          const btn = document.querySelector("[data-activates='" + dropdown.id + "']");
          closeNavDropdown(dropdown, btn);
        });
      }, { passive: true });

      if (mobileBreakpoint.matches) return;
      const leftBtn = qs(".scrollable-navbar__arrow--left", wrapper);
      const rightBtn = qs(".scrollable-navbar__arrow--right", wrapper);
      const listItems = Array.from(list.querySelectorAll(":scope > li"));
      const originalPaddingRight = parseFloat(getComputedStyle(list).paddingRight) || 0;

      let pageStarts = [0];
      let pageScrollTargets = [0];
      const LEFT_ARROW_WIDTH = 20;

      function computePageStarts() {
        const cw = list.clientWidth;
        pageStarts = [0];
        pageScrollTargets = [0];
        let pos = 0;
        while (true) {
          const rightEdge = pos + cw;
          const next = listItems.find(function (item) { return item.offsetLeft + item.offsetWidth > rightEdge; });
          if (!next) break;
          const pageStart = next.offsetLeft;
          const scrollTarget = Math.max(0, pageStart - LEFT_ARROW_WIDTH);
          if (scrollTarget <= pos) break;
          pageStarts.push(pageStart);
          pageScrollTargets.push(scrollTarget);
          pos = scrollTarget;
        }
      }

      // Extend scrollWidth so every page scroll target is a reachable scrollLeft value
      // (browser caps scrollLeft at scrollWidth - clientWidth).
      function ensurePagination() {
        list.style.paddingRight = originalPaddingRight + "px";
        const cw = list.clientWidth;
        if (!cw || pageScrollTargets.length <= 1) return;
        const lastTarget = pageScrollTargets[pageScrollTargets.length - 1];
        const neededSW = lastTarget + cw;
        if (neededSW > list.scrollWidth) {
          list.style.paddingRight = (originalPaddingRight + neededSW - list.scrollWidth) + "px";
        }
      }

      function getCurrentPageIndex() {
        for (var i = pageScrollTargets.length - 1; i >= 0; i--) {
          if (list.scrollLeft >= pageScrollTargets[i] - 1) return i;
        }
        return 0;
      }

      function update() {
        const hasOverflowLeft = list.scrollLeft > 1;
        const hasOverflowRight = list.scrollLeft + list.clientWidth < list.scrollWidth - 1;
        wrapper.classList.toggle("has-overflow-left", hasOverflowLeft);
        wrapper.classList.toggle("has-overflow-right", hasOverflowRight);
      }

      function updateCenter() {
        wrapper.classList.toggle("center", list.scrollWidth <= 1050);
        wrapper.classList.toggle("mobile-centered", list.scrollWidth <= 325);
      }

      const isHomeNavbar = !!wrapper.closest("#home-navbar");

      list.addEventListener("scroll", update, { passive: true });
      window.addEventListener("resize", function () {
        updateCenter();
        if (isHomeNavbar) { computePageStarts(); ensurePagination(); }
        update();
      });

      if (leftBtn) {
        leftBtn.addEventListener("click", function () {
          if (isHomeNavbar) {
            const idx = getCurrentPageIndex();
            if (idx > 0) list.scrollTo({ left: pageScrollTargets[idx - 1], behavior: "smooth" });
          } else {
            list.scrollBy({ left: -list.clientWidth, behavior: "smooth" });
          }
        });
      }
      if (rightBtn) {
        rightBtn.addEventListener("click", function () {
          if (isHomeNavbar) {
            const idx = getCurrentPageIndex();
            if (idx + 1 < pageScrollTargets.length) list.scrollTo({ left: pageScrollTargets[idx + 1], behavior: "smooth" });
          } else {
            list.scrollBy({ left: list.clientWidth, behavior: "smooth" });
          }
        });
      }

      document.fonts.ready.then(function () {
        updateCenter();
        if (isHomeNavbar) { computePageStarts(); ensurePagination(); }
        update();
      });
    });

    // Newsletter tooltip — toggle on trigger click, close on outside click
    qsa("[data-nl-tooltip-host]").forEach(function (host) {
      const trigger = qs("[data-nl-tooltip-trigger]", host);
      const tooltip = qs(".nl-tooltip", host);
      if (!trigger || !tooltip) return;

      trigger.addEventListener("click", function (event) {
        event.preventDefault();
        tooltip.toggleAttribute("hidden");
      });
    });

    document.addEventListener("click", function (event) {
      qsa(".nl-tooltip").forEach(function (tooltip) {
        if (tooltip.hasAttribute("hidden")) return;
        const host = tooltip.closest("[data-nl-tooltip-host]");
        if (host && !host.contains(event.target)) {
          tooltip.setAttribute("hidden", "");
        }
      });
    });

    // Keep variable assignment to preserve previous side effects.
    void isMobile;
  }); // end of document ready
})();
