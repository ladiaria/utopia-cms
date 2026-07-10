// Registration wall — ajax for the email step.
//
// The email form (step A) resolves to the login (existing account) or signup (new account) step. Submitting it over
// ajax swaps the wall content in place, so the reader keeps their scroll position instead of the article reloading
// from the top. Without this script the form posts normally and the server reloads the article on the resolved step,
// so the flow still works (progressive enhancement).
//
// Only the email step is intercepted. The login and signup steps post to the real views and do reload the page, which
// is fine: that is the end of the flow (the reader ends up logged in, or on the signup flow).
(function () {
  "use strict";

  var wall = document.querySelector(".registration-wall");
  if (!wall) return;

  var box = wall.querySelector(".registration-wall__box");

  // Only the email step posts to the resolver; login/signup post to the real login/signup views.
  function isEmailStep(form) {
    return form && /registration-wall\/email/.test(form.getAttribute("action") || "");
  }

  function bind() {
    var form = box.querySelector(".registration-wall__form");
    if (!isEmailStep(form)) return;

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var button = form.querySelector("[type=submit]");
      if (button) button.disabled = true;

      fetch(form.getAttribute("action"), {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
        },
        body: new FormData(form),
      })
        .then(function (response) {
          if (!response.ok) throw new Error("registration wall email step failed");
          return response.text();
        })
        .then(function (html) {
          box.innerHTML = html;
          // the email step can come back (an invalid email or too many attempts), so rebind it
          bind();
        })
        .catch(function () {
          // fall back to a normal submit (full reload) if the request could not be completed
          form.submit();
        });
    });
  }

  bind();
})();
