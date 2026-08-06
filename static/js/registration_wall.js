// Registration wall — ajax for the email and login steps, and the reveal button on the password fields.
//
// The email form (step A) resolves to the login (existing account), signup (new account) or google (account that can
// only be entered with Google, so there is no password to ask for) step, and the login form
// (step B) either logs the reader in or comes back with an error. Submitting them over ajax swaps the wall content in
// place, so the reader stays where they were instead of the article reloading from the top, and a rejected
// login is answered inside the article instead of on the full hard paywall page. Without this script both forms post
// normally and the server answers with a page load, so the flow still works (progressive enhancement).
//
// The signup step (step C) is intercepted for the same reason: a password that does not meet the requirements used to
// answer with the full signup page, throwing the reader out of the article; now the errors come back as this step and
// are shown in place. When it does succeed there is nothing to swap in, so the view answers with the destination and
// the script navigates there (the reader is sent to check their email).
(function () {
  "use strict";

  var wall = document.querySelector(".registration-wall");
  if (!wall) return;

  var box = wall.querySelector(".registration-wall__box");

  // Steps have different heights (signup is much taller than email), and the reader submits from the bottom of the
  // form: after the swap the new step often starts above the viewport, which on mobile means landing mid-form with
  // the title and the first fields out of sight. Keeping the scroll position is only right while the content stays
  // the same size, so put the wall back in view and move the focus into the new step.
  //
  // block:"nearest" scrolls the minimum needed: nothing while the wall already fits on screen, its top up under the
  // header when it does not or when it starts above it, and otherwise just enough to uncover its bottom. How much
  // room to leave at the top of the viewport is CSS, not a number here: scroll-padding-top (_utopia_base.scss) plus
  // the scroll-margin-top of .registration-wall (article/registration_wall.scss), which is what clears the sticky
  // header and, on the article detail, the breadcrumb pinned under it.
  function revealWall() {
    wall.scrollIntoView({
      block: "nearest",
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    });

    // The swap destroys whatever had the focus, dropping it on the body: without this a screen reader is told
    // nothing about the step that just arrived (a rejected password, the signup form) and the next Tab restarts
    // from the top of the document. The title is only a focus target once the step can be swapped, so the tabindex
    // is set here instead of in the markup, which without this script is never swapped at all.
    var title = box.querySelector(".registration-wall__title");
    if (title) {
      title.setAttribute("tabindex", "-1");
      title.focus({ preventScroll: true }); // the scroll above already placed the whole wall, not just the title
    }
  }

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
          revealWall();
        });
      })
      .catch(function () {
        // same fallback as the forms: let the browser do it, which reloads the article on the email step
        form.submit();
      });
  });

  // The email step posts to the resolver, which always answers with html. The login and signup steps post to their
  // views, which answer with html when they reject the attempt and with json when they succeed.
  function isEmailStep(form) {
    return /registration-wall\/email/.test(form.getAttribute("action") || "");
  }

  function isLoginStep(form) {
    return form.classList.contains("registration-wall__form--login");
  }

  function isSignupStep(form) {
    return form.classList.contains("registration-wall__form--signup");
  }

  function bind() {
    var form = box.querySelector(".registration-wall__form");
    if (!form || !(isEmailStep(form) || isLoginStep(form) || isSignupStep(form))) return;

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
            revealWall();
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
