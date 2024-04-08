function urlB64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
let bad_msg = 'El perfil no se pudo actualizar, intente más tarde.'
let good_msg = 'Perfil Actualizado.'

function msg(message) {
    return '<ul id="push-msg" class="messages unstyled ld-messages">' +
        '<li class="alert alert-success ld-message">' +
        message +
        '<button type="button" class="close ld-message__close js-dismiss-message">×</button>' +
        '</li>' +
        '</ul>';
}

let rp = function requestPermission(){
  if (('Notification' in window)) {
    Notification.requestPermission(status => {
      console.log('Notification permission status:', status);
      if(status === 'granted') subscribeUser();
    });
  }
};

function unsubscribeUser(){
  navigator.serviceWorker.getRegistration()
  .then(reg => reg.pushManager.getSubscription())
  .then(subscription => {
    if (subscription) {
      subscription_to_delete = subscription;
      setCookie('notifyme', "false", 1);
      deleteCookie('home_arriving', 1);
      return subscription.unsubscribe();
    }
  }).catch(err => {
    console.log('Error unsubscribing', err);
  }).then(() => {
    updateSubscriptionOnServer(null);
  });
}

function updateSubscriptionOnServer(subscription) {
  // Here's where you would send the subscription to the application server
  if (subscription) {
    fetch('/subscribe/', {
      method: 'POST',
      mode: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': Cookies.get('csrftoken')
      },
      body: JSON.stringify(subscription)
    }).then(response => response.json()).then(function(data){
      if(data['subscribed'] === 'false') {
        unsubscribeUser();
        if(getCookie('show_msg',1) == "true") {
          $("#push-msg").remove();
          $("#main-content").prepend(msg(bad_msg));
          setCookie('show_msg', "false", 1);
        }
      } else {
        if(getCookie('show_msg',1) == "true") {
          $("#push-msg").remove();
          $("#main-content").prepend(msg(good_msg));
          setCookie('show_msg', "false", 1);
        }
      }
    }).catch(err => {
      unsubscribeUser();
      if(getCookie('show_msg',1) == "true") {
        $("#push-msg").remove();
        $("#main-content").prepend(msg(bad_msg));
        setCookie('show_msg', "false", 1);
      }
      console.log(err);
    });
  } else {
    fetch('/subscribe/', {
      method: 'DELETE',
      mode: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': Cookies.get('csrftoken')
      },
      body: JSON.stringify(subscription_to_delete)
    }).then(response => response.json()).then(function(data){
      if(data['unsubscribed'] === 'true') {
        console.log('User unsubscribed');
        if(getCookie('show_msg',1) == "true") {
          $("#push-msg").remove();
          $("#main-content").prepend(msg(good_msg));
          setCookie('show_msg', "false", 1);
        }
      } else {
        if(getCookie('show_msg',1) == "true") {
          $("#push-msg").remove();
          $("#main-content").prepend(msg(bad_msg));
          setCookie('show_msg', "false", 1);
        }
      }
    }).catch(err => {
      console.log(err);
      if(getCookie('show_msg',1) == "true") {
        $("#push-msg").remove();
        $("#main-content").prepend(msg(bad_msg));
        setCookie('show_msg', "false", 1);
      }
    });
  }
}

function subscribeUser() {
  var reg;
  const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
  navigator.serviceWorker.getRegistration().then(function(swreg){
    reg = swreg;
    return swreg.pushManager.getSubscription();
  }).then(sub => {
    if(sub === null) {
      reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey
      }).then(subscription => {
        console.log('User is subscribed');
        setCookie('notifyme', "true", 1);
        updateSubscriptionOnServer(subscription);
      }).catch(err => {
        if (Notification.permission === 'denied') {
          console.warn('Permission for notifications was denied');
        } else {
          console.error('Failed to subscribe the user: ', err);
        }
      });
    } else {
      console.log('User already has a subscription');
      setCookie('notifyme', "true", 1);
    }
  });
}

function confirmFunction () {
  rp();
  $('.pwa-prompt').hide();
}

function cancelFunction () {
  $('.pwa-prompt').hide();
  setCookie('notifyme', "false", 1);
  deleteCookie('home_arriving', 1);
}

$(function(){
  navigator.permissions.query({name: 'notifications'}).then(function(result) {

    if (result.state == 'granted' || result.state == 'prompt') {

      if (getCookie('notifyme', 1) == null) {

        let now = new Date();
        const datesAreOnSameDay = (first, second) =>
          first.getFullYear() === second.getFullYear() &&
          first.getMonth() === second.getMonth() &&
          first.getDate() === second.getDate();

        if (window.location.pathname == '/') {
          if (!getCookie('home_arriving', 1)) {
            // This is the first time in the home page, then set the moment variable to 1 and the time
            // variable to current time.
            setCookie('home_arriving', JSON.stringify({'moment': 1, 'time': now}), 1);
          } else {
            // 2nd time or more.
            let home_arriving_value = JSON.parse(getCookie('home_arriving', 1));
            if (
              home_arriving_value.moment == 1 && datesAreOnSameDay(new Date(home_arriving_value.time), now)
            ) {
              // 2nd time in the same day, offer to allow notifications only if the NLs header wasn't rendered.
              if($("#choose-nl-container").length == 0){
                $('.pwa-prompt').show();
                setCookie('home_arriving', JSON.stringify({'moment': 2, 'time': now}), 1);
              }
            } else {
              // Neither first nor 2nd in the same day, so, check if last arrived date is +24h ago;
              // to only offer allow notifications once per day.
              if (new Date(home_arriving_value.time).getDate() + (24 * 60 * 60 * 1000) < now.getTime()) {
                setCookie('home_arriving', JSON.stringify({'moment': 1, 'time': now}), 1);
              }
            }
          }
        }

        if (
          getCookie(userName) == 'null'
          || getCookie('home_arriving', 1) && JSON.parse(getCookie('home_arriving', 1)).moment == 1
        ) {
          // TODO: check this condition with UX
          // If current location contains 'utm_source=newsletter' I got here from NL, so I will show the push
          // notification offer only if also the homepage was visited once.
          if (window.location.href.search('utm_source=newsletter') > 0) {
            let targetDiv = $('.pwa-prompt')
            if (targetDiv.length) {
              targetDiv.show();
              // set home arrived to moment 2 to wait at least 24hs to offer again
              setCookie('home_arriving', JSON.stringify({'moment': 2, 'time': now}), 1);
            }
          }
        }

      }

    } else {
      deleteCookie('notifyme', 1);
      deleteCookie('home_arriving', 1);
    }

  });
});
