(function () {
  "use strict";

  var config = window.LDArticleConfig || {};

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function getCookie(name) {
    if (window.Cookies && typeof window.Cookies.get === "function") {
      return window.Cookies.get(name);
    }

    var cookieString = document.cookie || "";
    var cookies = cookieString.split(";");
    for (var i = 0; i < cookies.length; i += 1) {
      var cookie = cookies[i].trim();
      if (cookie.indexOf(name + "=") === 0) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
  }

  function openAuthModal() {
    var modals = qsa(".modal");

    if (window.M && window.M.Modal) {
      modals.forEach(function (modalEl) {
        var instance = window.M.Modal.getInstance(modalEl) || window.M.Modal.init(modalEl);
        if (instance && typeof instance.open === "function") {
          instance.open();
        }
      });
      return;
    }

    modals.forEach(function (modalEl) {
      modalEl.classList.add("active");
    });
  }

  function requestGet(url, onSuccess) {
    fetch(url, {
      method: "GET",
      credentials: "same-origin"
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("GET request failed");
        }
        return response.text();
      })
      .then(function () {
        if (typeof onSuccess === "function") {
          onSuccess();
        }
      })
      .catch(function () {});
  }

  function requestPostForm(url, data, onSuccess) {
    var formData = new URLSearchParams();
    Object.keys(data).forEach(function (key) {
      formData.append(key, data[key]);
    });

    fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: formData.toString()
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("POST request failed");
        }
        return response.text();
      })
      .then(function () {
        if (typeof onSuccess === "function") {
          onSuccess();
        }
      })
      .catch(function () {});
  }

  function trackMostReadClicks() {
    qsa("p.atitlelist a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (typeof window.ga === "function") {
          window.ga("send", "event", "masleidos", "Click", "Article_viewpayw");
        }
      });
    });
  }

  function initSignupwallPopup() {
    if (!config.signupwallEnabled) {
      return;
    }

    var popup = qs("#subscribe-popup");
    if (!popup) {
      return;
    }

    if (window.M && window.M.Modal) {
      window.M.Modal.getInstance(popup) || window.M.Modal.init(popup);
    }

    popup.addEventListener("hidden.bs.modal", function () {
      var signupwall = qs("#signupwall");
      if (signupwall) {
        signupwall.style.display = signupwall.style.display === "none" ? "" : "none";
      }
    });
  }

  function initAudioReadLaterButtons() {
    qsa(".ld-audio__action-bar-read-later").forEach(function (button) {
      button.addEventListener("click", function () {
        if (!config.isAuthenticated) {
          openAuthModal();
          return;
        }

        requestGet(config.followUrl, function () {
          qsa(".ld-audio__action-bar-read-later").forEach(function (el) {
            el.classList.add("hidden");
          });
          qsa(".ld-audio__action-bar-read-later-saved").forEach(function (el) {
            el.classList.remove("hidden");
          });
        });
      });
    });

    qsa(".ld-audio__action-bar-read-later-saved").forEach(function (button) {
      button.addEventListener("click", function () {
        if (!config.isAuthenticated) {
          openAuthModal();
          return;
        }

        requestGet(config.unfollowUrl, function () {
          qsa(".ld-audio__action-bar-read-later").forEach(function (el) {
            el.classList.remove("hidden");
          });
          qsa(".ld-audio__action-bar-read-later-saved").forEach(function (el) {
            el.classList.add("hidden");
          });
        });
      });
    });
  }

  function initReadLaterButtons() {
    qsa(".read-later__add").forEach(function (button) {
      button.addEventListener("click", function () {
        if (!config.isAuthenticated) {
          openAuthModal();
          return;
        }

        requestGet(config.followUrl, function () {
          qsa(".read-later__add").forEach(function (el) {
            el.classList.add("hide");
          });
          qsa(".read-later__add__info").forEach(function (el) {
            el.classList.add("hide");
          });

          var savedInfoList = qsa(".read-later__saved__info");
          if (savedInfoList[1]) {
            savedInfoList[1].classList.remove("hide");
          }

          qsa(".read-later__saved").forEach(function (el) {
            el.classList.remove("hide");
          });
          qsa(".read-later__saved__info.first").forEach(function (el) {
            el.classList.remove("hide");
          });
          qsa("a.read-later__saved.first").forEach(function (el) {
            el.classList.remove("hide");
          });
        });
      });
    });

    qsa("a.read-later__saved").forEach(function (button) {
      button.addEventListener("click", function () {
        if (!config.isAuthenticated) {
          openAuthModal();
          return;
        }

        requestGet(config.unfollowUrl, function () {
          qsa("a.read-later__add").forEach(function (el) {
            el.classList.remove("hide");
          });
          qsa(".read-later__add__info").forEach(function (el) {
            el.classList.remove("hide");
          });
          qsa(".read-later__saved__info").forEach(function (el) {
            el.classList.add("hide");
          });
          qsa("a.read-later__saved").forEach(function (el) {
            el.classList.add("hide");
          });
        });
      });
    });

    if (config.followed) {
      var firstSaved = qs("a.read-later__saved");
      if (firstSaved) {
        firstSaved.addEventListener("click", function () {
          if (!config.isAuthenticated) {
            openAuthModal();
            return;
          }

          requestGet(config.unfollowUrl, function () {
            qsa("a.read-later__saved").forEach(function (savedEl) {
              savedEl.classList.add("hide");
              if (savedEl.previousElementSibling) {
                savedEl.previousElementSibling.classList.add("hide");
              }
            });

            qsa(".read-later__add").forEach(function (addEl) {
              addEl.classList.remove("hide");
              if (addEl.nextElementSibling) {
                addEl.nextElementSibling.classList.remove("hide");
              }
            });
          });
        });
      }
    }
  }

  function initSharePopup() {
    var shareButton = qs("#action-bar__share-button");
    var popup = qs(".popup-compartir");

    if (!shareButton || !popup) {
      return;
    }

    shareButton.addEventListener("click", function () {
      popup.classList.toggle("visible");
    });

    document.addEventListener("click", function (event) {
      if (!event.target.closest(".popup-compartir, #action-bar__share-button")) {
        popup.classList.remove("visible");
        qsa(".copy-link-to-clipboard span").forEach(function (span) {
          span.textContent = "Copiar link";
        });
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" || event.keyCode === 27) {
        popup.classList.remove("visible");
        qsa(".copy-link-to-clipboard span").forEach(function (span) {
          span.textContent = "Copiar link";
        });
      }
    });

    popup.addEventListener("click", function (event) {
      event.stopPropagation();
    });
  }

  function initIpfsButton() {
    qsa("a.open-ipfs").forEach(function (button) {
      button.addEventListener("click", function () {
        window.open(config.ipfsArticleUrl, "Ver en IPFS");
      });
    });
  }

  function initFavButtons() {
    qsa("a.fav__saved").forEach(function (button) {
      button.addEventListener("click", function () {
        requestPostForm(
          config.favUrl,
          {
            target_model: "core.Article",
            target_object_id: String(config.articleId)
          },
          function () {
            qsa(".fav .info").forEach(function (info) {
              info.classList.add("hide");
            });

            qsa("a.fav__saved").forEach(function (savedEl) {
              var next = savedEl.nextElementSibling;
              var nextNext = next ? next.nextElementSibling : null;

              if (next) {
                next.classList.add("hide");
              }
              if (nextNext) {
                nextNext.classList.remove("hide");
              }

              savedEl.classList.add("hide");
              if (savedEl.previousElementSibling) {
                savedEl.previousElementSibling.classList.add("hide");
              }
              if (savedEl.parentElement && savedEl.parentElement.lastElementChild) {
                savedEl.parentElement.lastElementChild.classList.remove("hide");
              }
            });
          }
        );
      });
    });

    qsa("a.fav__add").forEach(function (button) {
      button.addEventListener("click", function () {
        if (!config.isAuthenticated) {
          openAuthModal();
          return;
        }

        requestPostForm(
          config.favUrl,
          {
            target_model: "core.Article",
            target_object_id: String(config.articleId)
          },
          function () {
            qsa("a.fav__add").forEach(function (addEl) {
              addEl.classList.add("hide");

              var prev = addEl.previousElementSibling;
              var prevPrev = prev ? prev.previousElementSibling : null;

              if (prev) {
                prev.classList.remove("hide");
              }
              if (prevPrev) {
                prevPrev.classList.remove("hide");
              }
              if (addEl.parentElement && addEl.parentElement.lastElementChild) {
                addEl.parentElement.lastElementChild.classList.add("hide");
              }
            });
          }
        );
      });
    });
  }

  function initAudioProgressTracking() {
    if (!config.isSubscriber) {
      return;
    }

    var audioEl = qs(".ld-audio__audio");
    if (!audioEl) {
      return;
    }

    var actTime = -1;

    audioEl.addEventListener("timeupdate", function () {
      var trackLength = audioEl.duration;
      var secs = audioEl.currentTime;

      if (!trackLength || !isFinite(trackLength)) {
        return;
      }

      var percent = (secs / trackLength) * 100;
      var progress = Math.floor(percent);
      var roundedPct = "0";

      if (progress > actTime && progress % 5 === 0) {
        actTime = progress;

        if (actTime > 70) {
          roundedPct = "75";
        } else if (actTime > 45) {
          roundedPct = "50";
        } else if (actTime > 20) {
          roundedPct = "25";
        }

        requestPostForm(config.audioStatsUrl, {
          audio_id: config.audioId || "",
          subscriber_id: config.subscriberId || "",
          percentage: roundedPct
        });
      }
    });
  }

  function init() {
    trackMostReadClicks();
    initSignupwallPopup();
    initAudioReadLaterButtons();
    initReadLaterButtons();
    initSharePopup();
    initIpfsButton();
    initFavButtons();
    initAudioProgressTracking();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.copyToClipboard = function copyToClipboard(element, tooltipclass, withTooltip) {
    var source = qs(element);
    var text = source ? source.textContent : "";

    var writeTextPromise;
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      writeTextPromise = navigator.clipboard.writeText(text);
    } else {
      var tempInput = document.createElement("input");
      tempInput.value = text;
      document.body.appendChild(tempInput);
      tempInput.select();
      document.execCommand("copy");
      tempInput.remove();
      writeTextPromise = Promise.resolve();
    }

    writeTextPromise.catch(function () {}).finally(function () {
      if (tooltipclass) {
        qsa(tooltipclass).forEach(function (tooltip) {
          tooltip.classList.remove("off");
          tooltip.textContent = "Enlace copiado";

          setTimeout(function () {
            tooltip.classList.add("off");
          }, 1000);

          setTimeout(function () {
            tooltip.textContent = "";
          }, 1200);
        });
      }

      if (withTooltip) {
        qsa(".copy-link-to-clipboard span").forEach(function (span) {
          span.textContent = "Link copiado";
        });
      }
    });
  };
})();
