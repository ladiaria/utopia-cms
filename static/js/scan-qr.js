/* global SCAN_QR_CONFIG, Html5Qrcode, $ */

let currentScannedCode = null;

// --- QR scan callbacks ---

function onScanSuccess(decodedText) {
  const expectedPrefix = SCAN_QR_CONFIG.siteUrl + "comunidad/verify-registro/";

  if (!decodedText.startsWith(expectedPrefix)) {
    document.getElementById("error-message").innerHTML = "Código QR inválido";
    return;
  }

  const urlParts = decodedText.split("/");
  const code = urlParts[urlParts.length - 2];

  // Same code as what's already loaded — do nothing, avoid spamming the API at 10fps
  if (code === currentScannedCode) return;
  currentScannedCode = code;

  document.getElementById("id_code").value = code;

  const benefitName = document.getElementById("benefit-name");
  const submitButton = document.getElementById("submit-button");
  const messageDiv = document.getElementById("qr-scanned-successfully");

  // Reset UI for the new code
  submitButton.disabled = true;
  submitButton.classList.remove("with-tick");
  messageDiv.innerText = "";
  messageDiv.classList.remove("success", "error");

  $.ajax({
    type: "POST",
    url: SCAN_QR_CONFIG.checkQrCodeUrl,
    data: {
      code: code,
      csrfmiddlewaretoken: document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
    success: function (response) {
      benefitName.innerText = response.name;
      benefitName.classList.remove("error");
      submitButton.disabled = false;
    },
    error: function (xhr) {
      const response = JSON.parse(xhr.responseText);
      benefitName.innerText = response.error || "Ocurrió un error. Por favor, intenta de nuevo.";
      benefitName.classList.add("error");
      submitButton.disabled = true;
    },
  });
}

function onScanFailure() {
  // Silently ignore scan failures
}

// --- QR reader init ---

const html5QrCode = new Html5Qrcode("qr-reader");
html5QrCode.start(
  { facingMode: "environment" },
  { fps: 10, qrbox: { width: 150, height: 150 } },
  onScanSuccess,
  onScanFailure
);

// --- Form submission ---

document.getElementById("scan-qr-form").addEventListener("submit", function (event) {
  event.preventDefault();

  const form = this;
  const formData = new FormData(form);
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

  fetch(form.action, {
    method: "POST",
    body: formData,
    headers: {
      "X-CSRFToken": csrfToken,
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      const messageDiv = document.getElementById("qr-scanned-successfully");
      const submitBtn = document.getElementById("submit-button");

      submitBtn.disabled = true;
      submitBtn.classList.remove("with-tick");

      if (data.success) {
        messageDiv.innerText = data.message;
        messageDiv.classList.remove("error");
        messageDiv.classList.add("success");
        submitBtn.classList.add("with-tick");
      } else {
        messageDiv.innerText = data.message;
        messageDiv.classList.remove("success");
        messageDiv.classList.add("error");
      }
    })
    .catch(() => {
      // Silently ignore fetch errors
    });
});
