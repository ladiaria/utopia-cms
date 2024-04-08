function setNotificationCheckStatus() {
  navigator.serviceWorker.getRegistration().then(reg => {
    return reg.pushManager.getSubscription();
  }).then(subscription => {
    if(getCookie('notifyme', 1) == null) {
      setCookie('notifyme', "false", 1);
    }
    if(subscription && getCookie('notifyme', 1) == "true") {
      const switchElement = document.getElementById("notificaciones").querySelector(".switch-container");
      revertSwitch(switchElement);  // Since it always load in false, we revert to true
    }
  }).catch(err => {
    console.log('Error initializing push notifications switch', err);
  });
}

function handlePushNotificationSwitchChange(switchHTMLElement, inputId) {
  navigator.permissions.query({ name: 'notifications' }).then(function(result) {
    if(result.state === 'denied'){
      // TODO: change alert merging with UX tooltip/new-text design
      showNotification({
        type: "error",
        text: "Debe habilitar las notificaciones en su navegador."
      });
      revertSwitch(switchHTMLElement);
      return;
    }
  });

  setCookie('show_msg', "true", 1);

  if($("#" + inputId).prop('checked') && getCookie('notifyme', 1) == "false") {
    rp();
    showNotification({
      text: "Tus cambios fueron guardados"
    });
  } else if(!$("#" + inputId).prop('checked') && getCookie('notifyme', 1) == "true") {
    // TODO: DELETE can return 400 (and then a js error) if there is no DeviceSubscribed to remove.
    unsubscribeUser();
  }
}
