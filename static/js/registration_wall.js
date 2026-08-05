// Registration wall — ajax for the email and login steps, and the reveal button on the password fields.
//
// The email form (step A) resolves to the login (existing account) or signup (new account) step, and the login form
// (step B) either logs the reader in or comes back with an error. Submitting them over ajax swaps the wall content in
// place, so the reader keeps their scroll position instead of the article reloading from the top, and a rejected
// login is answered inside the article instead of on the full hard paywall page. Without this script both forms post
// normally and the server answers with a page load, so the flow still works (progressive enhancement).
//
// The signup step is not intercepted: it is the end of the flow, and it leaves the article anyway (the reader is sent
// to check their email).
(function () {
  "use strict";

  var wall = document.querySelector(".registration-wall");
  if (!wall) return;

  var box = wall.querySelector(".registration-wall__box");

  // Reveal button on the password fields (login and signup steps). Delegated on the wall instead of bound to each
  // button, because the step markup inside __box is replaced over ajax and a bound handler would not survive it.
  wall.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest(".registration-wall__reveal");
    if (!button) return;
    var input = document.getElementById(button.getAttribute("data-reveal-target"));
    if (!input) return;
    var reveal = input.getAttribute("type") === "password";
    input.setAttribute("type", reveal ? "text" : "password");
    button.classList.toggle("registration-wall__reveal--revealed", reveal);
    button.setAttribute("aria-pressed", reveal ? "true" : "false");
    button.setAttribute("aria-label", reveal ? "Ocultar contraseña" : "Mostrar contraseña");
  });

  // "Editar" next to the locked email of the signup step. The button is tied to #registration-wall-back with the
  // form attribute, so without this it posts on its own and the article reloads on the email step; here it is sent
  // over ajax instead, to swap the step in place like the other two do. Delegated for the same reason as the reveal
  // button: the markup inside __box is replaced over ajax.
  wall.addEventListener("click", function (event) {
    var edit = event.target.closest && event.target.closest(".registration-wall__email-edit");
    if (!edit) return;
    var form = document.getElementById(edit.getAttribute("form"));
    if (!form) return;
    event.preventDefault();

    fetch(form.getAttribute("action"), {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
      },
      body: new FormData(form),
    })
      .then(function (response) {
        if (!response.ok) throw new Error("registration wall step failed");
        return response.text().then(function (html) {
          box.innerHTML = html;
          bind();
        });
      })
      .catch(function () {
        // same fallback as the forms: let the browser do it, which reloads the article on the email step
        form.submit();
      });
  });

  // The email step posts to the resolver, which always answers with html. The login step posts to the login view,
  // which answers with html when it rejects the attempt and with json when it succeeds.
  function isEmailStep(form) {
    return /registration-wall\/email/.test(form.getAttribute("action") || "");
  }

  function isLoginStep(form) {
    return form.classList.contains("registration-wall__form--login");
  }

  function bind() {
    var form = box.querySelector(".registration-wall__form");
    if (!form || !(isEmailStep(form) || isLoginStep(form))) return;

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
          if (!response.ok) throw new Error("registration wall step failed");
          if ((response.headers.get("Content-Type") || "").indexOf("application/json") !== -1) {
            // logged in: the view hands over where to go instead of a 302, which fetch would have followed itself,
            // leaving the script with the article's html and no way to tell it apart from a step partial
            return response.json().then(function (data) {
              window.location.assign(data.redirect);
            });
          }
          return response.text().then(function (html) {
            box.innerHTML = html;
            // the step can come back on itself (an invalid email, too many attempts, a rejected login), so rebind
            bind();
          });
        })
        .catch(function () {
          // fall back to a normal submit (full reload) if the request could not be completed
          form.submit();
        });
    });
  }

  bind();
})();
