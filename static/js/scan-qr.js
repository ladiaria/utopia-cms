/* global SCAN_QR_CONFIG, Html5Qrcode, $ */

// --- QR scan callbacks ---

function onScanSuccess(decodedText) {
  const expectedPrefix = SCAN_QR_CONFIG.siteUrl + "comunidad/verify-registro/";

  if (!decodedText.startsWith(expectedPrefix)) {
    document.getElementById("error-message").innerHTML = "Código QR inválido";
    return;
  }

  const urlParts = decodedText.split("/");
  const code = urlParts[urlParts.length - 2];

  document.getElementById("id_code").value = code;

  const infoContainer = document.getElementById("info-container");
  const submitButton = document.getElementById("submit-button");

  $.ajax({
    type: "POST",
    url: SCAN_QR_CONFIG.checkQrCodeUrl,
    data: {
      code: code,
      csrfmiddlewaretoken: document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
    success: function (response) { // Scan que leyó el QR
      infoContainer.innerText = response.name;
      infoContainer.classList.remove("error");
      submitButton.disabled = false;
      submitButton.classList.remove("hidden");
      document.getElementById("qr-scanned-successfully").innerHTML = "";
    },
    error: function (xhr) { // Scan con ERror
      const response = JSON.parse(xhr.responseText);
      const errorMessages = {
        404: response.error || "Código QR no encontrado.",
        400: response.error || "QR inválido.",
      };
      infoContainer.innerText =
        errorMessages[xhr.status] || "Ocurrió un error. Por favor, intenta de nuevo.";
      infoContainer.classList.add("error");
      document.getElementById("qr-scanned-successfully").innerHTML = "";
      document.getElementById("submit-button").disabled = true;
      document.getElementById("submit-button").classList.add("hidden");
    },
  });
}

function onScanFailure() {
  // Silently ignore scan failures
}

// --- QR reader init ---
console.log(SCAN_QR_CONFIG.checkQrCodeUrl);

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
      const submitButton = document.getElementById("submit-button");
      const infoContainer = document.getElementById("info-container");

      if (data.success) { // QR Confirmado
        messageDiv.classList.remove("hidden");
        messageDiv.innerText = data.message;

        infoContainer.classList.remove("error");
        infoContainer.classList.add("hidden");

        submitButton.disabled = true;
        submitButton.classList.add("with-tick");

        setTimeout(function () {
          messageDiv.classList.add("hidden");
          infoContainer.innerText = "Escanear QR de la entrada";
          infoContainer.classList.remove("hidden");
          submitButton.disabled = false;
          submitButton.classList.remove("with-tick");
          submitButton.classList.add("hidden");
        }, 1000);

      } else { // QR con error
        infoContainer.innerText = data.message;
        infoContainer.classList.add("error");

        submitButton.classList.add("hidden");
      }
    })
    .catch(() => {
      // Silently ignore fetch errors
    });
});
