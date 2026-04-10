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

// Helper function to capture errors in Sentry with context
function capturePushNotificationError(error, context, level = 'error') {
  if (typeof Sentry !== 'undefined') {
    Sentry.withScope(function(scope) {
      scope.setTag('feature', 'push_notifications');
      scope.setContext('push_notification_context', context);
      if (level === 'warning') {
        scope.setLevel('warning');
      }
      if (error instanceof Error) {
        Sentry.captureException(error);
      } else {
        Sentry.captureMessage(String(error), level);
      }
    });
  }
  // Always log to console for debugging
  if (level === 'warning') {
    console.warn(context.action + ':', error);
  } else {
    console.error(context.action + ':', error);
  }
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
      if(status === 'granted') {
        subscribeUser();
      } else if(status === 'default') {
        // User dismissed the browser prompt without choosing: treat like "Ahora no"
        var count = parseInt(localStorage.getItem('push_prompt_dismiss_count') || '0', 10);
        localStorage.setItem('push_prompt_dismiss_count', count + 1);
        localStorage.setItem('push_prompt_dismiss_at', Date.now());
      }
    });
  }
};


function unsubscribeUser(){
  navigator.serviceWorker.getRegistration()
  .then(reg => reg.pushManager.getSubscription())
  .then(subscription => {
    // Always update cookie state, regardless of subscription existence
    setCookie('notifyme', "false", 1);

    if (subscription) {
      subscription_to_delete = subscription;
      return subscription.unsubscribe();
    }
  }).catch(err => {
    capturePushNotificationError(err, {
      action: 'unsubscribeUser',
      step: 'getSubscription_or_unsubscribe'
    });
    // Also set cookie to false on error
    setCookie('notifyme', "false", 1);
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
      capturePushNotificationError(err, {
        action: 'updateSubscriptionOnServer',
        step: 'POST_subscribe',
        method: 'POST'
      });
      unsubscribeUser();
      if(getCookie('show_msg',1) == "true") {
        $("#push-msg").remove();
        $("#main-content").prepend(msg(bad_msg));
        setCookie('show_msg', "false", 1);
      }
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
      capturePushNotificationError(err, {
        action: 'updateSubscriptionOnServer',
        step: 'DELETE_subscribe',
        method: 'DELETE'
      });
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
          capturePushNotificationError('Permission for notifications was denied', {
            action: 'subscribeUser',
            step: 'pushManager_subscribe',
            permission: 'denied'
          }, 'warning');
        } else {
          capturePushNotificationError(err, {
            action: 'subscribeUser',
            step: 'pushManager_subscribe',
            permission: Notification.permission
          });
        }
      });
    } else {
      console.log('User already has a subscription');
      setCookie('notifyme', "true", 1);
    }
  });
}

var pushPromptShowTimer = null;
var pushPromptAutoHideTimer = null;

function confirmFunction () {
  clearTimeout(pushPromptAutoHideTimer);
  rp();
  $('.pwa-prompt').hide();
}

function cancelFunction () {
  clearTimeout(pushPromptAutoHideTimer);
  $('.pwa-prompt').hide();
  var count = parseInt(localStorage.getItem('push_prompt_dismiss_count') || '0', 10);
  localStorage.setItem('push_prompt_dismiss_count', count + 1);
  localStorage.setItem('push_prompt_dismiss_at', Date.now());
}

$(function(){
  // Check device support: must have Notification API, PushManager, and not be iOS
  if (!('Notification' in window) || !('PushManager' in window)) return;
  if (/iPad|iPhone|iPod/.test(navigator.userAgent)) return;

  // Don't show if permission was denied
  if (Notification.permission === 'denied') return;

  // Don't show if already subscribed
  if (getCookie('notifyme', 1) === 'true') return;

  // Check localStorage dismiss limits (max 3 dismissals)
  var dismissCount = parseInt(localStorage.getItem('push_prompt_dismiss_count') || '0', 10);
  if (dismissCount >= 3) return;

  // Check if 7 days have passed since last dismissal
  if (dismissCount > 0) {
    var dismissAt = localStorage.getItem('push_prompt_dismiss_at');
    if (dismissAt) {
      var sevenDays = 7 * 24 * 60 * 60 * 1000;
      if (Date.now() - parseInt(dismissAt, 10) < sevenDays) return;
    }
  }

  // Show modal after 20 seconds
  pushPromptShowTimer = setTimeout(function() {
    $('.pwa-prompt').show();

    // Auto-hide after another 20 seconds (40s total from page load)
    pushPromptAutoHideTimer = setTimeout(function() {
      $('.pwa-prompt').hide();
      // If user previously dismissed, reset the 7-day timer (don't increment count)
      if (parseInt(localStorage.getItem('push_prompt_dismiss_count') || '0', 10) > 0) {
        localStorage.setItem('push_prompt_dismiss_at', Date.now());
      }
    }, 20000);
  }, 20000);
});
