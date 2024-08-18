// Register service worker and update it
if (!getCookie('no_a2hs') || getCookie('no_a2hs') == "false") {
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', {updateViaCache: 'none'});
        navigator.serviceWorker.getRegistrations().then(function (registrations) {
            for (let registration of registrations) {
                registration.update();
            }
        });
    }
    if (typeof(pwa_function) !== "undefined" && pwa_function) {
        pwa_handle();
    }
}
