// shows a notification text info in the page (this is not the "push notification")
function showNotification(notification) {
  const isError = notification.type === "error";
  const notificationBox = document.querySelector("#edit_profile_notification");
  if (!notificationBox) return;
  notificationBox.style.display = "flex";
  notificationBox.classList.remove("error");
  if (isError) notificationBox.classList.add("error");
  notificationBox.querySelector("p").textContent = notification.text;
  setTimeout(function () {
    notificationBox.style.display = "none";
  }, isError ? 3000 : 2000);
}

// function to revert a switch value
function revertSwitch(switchHTMLElement) {
  const input = switchHTMLElement.querySelector('input[type="checkbox"]');
  const offLabel = switchHTMLElement.querySelector('.off');
  const onLabel = switchHTMLElement.querySelector('.on');
  const slider = switchHTMLElement.querySelector(".slider");
  input.checked = !input.checked;
  slider.style.backgroundColor = input.checked ? "#6FCF97" : "#ccc";
  offLabel.style.display = input.checked ? "none" : "inline-block";
  onLabel.style.display = input.checked ? "inline-block" : "none";
}

// handler for the switches that are not the push_notification one
function handleNewsletterSwitchChange(newsletterUrl, data, switchHTMLElement) {
  $.ajax({
    type: "POST",
    data: data,
    url: newsletterUrl,
    cache: false,
    success: function (html, textStatus) {
      showNotification({
        text: "Tus cambios fueron guardados"
      });
    },
    error: function (XMLHttpRequest, textStatus, errorThrown) {
      showNotification({
        text: "No se pudieron guardar los cambios, intentá de nuevo más tarde",
        type: "error",
        duration: 3000,
      });
      setTimeout(function () {
        revertSwitch(switchHTMLElement)
      }, 250);
    }
  });
}

// initialize newsletter header subscribe button
function nl_header_subscribe_init() {
  const config = window.NL_HEADER_CONFIG;
  const btn = document.querySelector('.newsletter-header');
  if (!config || !btn) return;

  btn.addEventListener('click', function() {
    const textSpan = btn.querySelector('.newsletter-header__text');
    if (config.isAnonymous) {
      if (textSpan) textSpan.textContent = config.anonymousMessage;
      return;
    }
    $.ajax({
      type: 'POST',
      url: config.subscribeUrl,
      data: { [config.dataKey]: true },
      success: function() {
        if (textSpan) textSpan.textContent = config.successMessage;
        btn.classList.add('newsletter-header--active');
        btn.disabled = true;
      },
      error: function() {
        if (textSpan) textSpan.textContent = 'No se pudo suscribir, intentá de nuevo';
      }
    });
  });
}

// set switch change events
function switch_change_events(switches, push_notifications_keys_set, callbackFunction) {
  for (let i = 0; i < switches.length; i++) {
    const switchElement = switches[i];
    const input = switchElement.querySelector('input[type="checkbox"]');
    const dataKey = input.getAttribute('data-key');
    const dataBouncer = eval(input.getAttribute('data-bouncer'));
    const offLabel = switchElement.querySelector('.off');
    const onLabel = switchElement.querySelector('.on');
    if (offLabel) offLabel.style.display = input.checked ? "none" : "inline-block";
    if (onLabel) onLabel.style.display = input.checked ? "inline-block" : "none";

    input.addEventListener("change", () => {
      const slider = switchElement.querySelector(".slider");
      const newsletterUrl = input.getAttribute('data-url');
      slider.style.backgroundColor = input.checked ? "#6FCF97" : "#ccc";
      if (offLabel) offLabel.style.display = input.checked ? "none" : "inline-block";
      if (onLabel) onLabel.style.display = input.checked ? "inline-block" : "none";
      if (input.id == "allow_notification") {
        if (push_notifications_keys_set) {
          handlePushNotificationSwitchChange(switchElement, input.id);
        }
      } else {
        handleNewsletterSwitchChange(newsletterUrl, { [dataKey]: input.checked }, switchElement);
        // disable input after a bouncer NL or communication deactivation
        if (["nl_subscribe", "com_subscribe"].includes(dataKey) && !input.checked && dataBouncer) {
          input.setAttribute("disabled", "disabled");
        }
      }
      if (callbackFunction) callbackFunction(input);
    });
  }
}
