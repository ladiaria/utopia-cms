function getCookie(name, userData=0) {
    // userData must be 1 if you want the cookie for the user in the current session
    if (userData == 1)
    {
        var cname = name;
        name = userName;
    }
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    if(cookieValue === 'null' && userData == 1)
        cookieValue = null;

    if(userData == 1 && cookieValue != null){
        return JSON.parse(cookieValue)[cname];
    }
    else
        return cookieValue;
}

function setCookie(cname, cvalue, userData=0) {
    var d = new Date();
    d.setTime(d.getTime() + (20000*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();

    if (userData == 1)
        {
            var propertyName = cname;
            var object = {};
            object[propertyName] = cvalue;
            let userNameFromCookie = getCookie(userName);
            if(userNameFromCookie != null && userNameFromCookie != 'null')
                {
                    var tmp = Object.assign(JSON.parse(userNameFromCookie), object);
                }
                else
                    var tmp = Object.assign({}, object);
            cvalue = JSON.stringify(tmp);
        cname = userName;
        }
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

function deleteCookie(cname, userData=0){
    if(userData == 1)
    {
        let userNameFromCookie = getCookie(userName);
        if(userNameFromCookie != null && userNameFromCookie != 'null')
            {
            var tmp = JSON.parse(userNameFromCookie);
            delete tmp[cname];
            setCookie(userName, JSON.stringify(tmp));
            }
    }
    else
        document.cookie = cname + "=; expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;";
}

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

    // Code to handle install prompt on desktop
    let deferredPrompt;
    let addBtn = '';
    let noshow = '';
    let undo = '';
    let section = '';
    let dismissed = '';
    let dismiss = '';
    let install_section = '';
    window.addEventListener('beforeinstallprompt', (e) => {
        // Prevent Chrome 67 and earlier from automatically showing the prompt
        e.preventDefault();
        // Stash the event so it can be triggered later.
        deferredPrompt = e;

        // Update UI (only section in the topbar)
        section_top = document.querySelector('.a2hs-section-top');
        if (section_top) {
            main_header = document.getElementById('main-header');
            main_header.classList.add("install-pwa");
            section_top.style.display = 'block';
            addBtn_top = document.querySelector('.a2hs-btn-top');

            // install button
            if (addBtn_top) {
                addBtn_top.addEventListener('click', (e) => {
                    e.preventDefault();
                    // Show the prompt
                    deferredPrompt.prompt();
                    // Wait for the user to respond to the prompt
                    deferredPrompt.userChoice.then((choiceResult) => {
                        if (choiceResult.outcome === 'accepted') {
                            // hide our user interface that shows our A2HS button
                            section_top.style.display = 'none';
                            main_header.classList.remove('install-pwa');
                        }
                        deferredPrompt = null;
                    });
                });
            }
        }

        // Update UI to notify the user they can add to home screen (section in pwa-module.html)
        section = document.querySelector('.a2hs-section');
        if (section) {
            section.style.display = 'block';
            addBtn = document.querySelector('.a2hs-btn');
            noshow = document.querySelector('.no_a2hs');
            install_section = document.querySelector('.install-section');
            undo = document.querySelector('.undo');
            dismissed = document.querySelector('.dismissed');
            dismiss = document.querySelector('.dismiss');

            //no show a2hs anymore
            if (noshow) {
                noshow.addEventListener('click', (e) => {
                    e.preventDefault();
                    dismiss.style.display = 'none';
                    install_section.style.display = 'none';
                    setCookie('no_a2hs', true);
                    dismissed.style.display = 'block';

                });
            }

            //undo no show a2hs anymore
            if (undo) {
                undo.addEventListener('click', (e) => {
                    e.preventDefault();
                    setCookie('no_a2hs', false);
                    dismissed.style.display = 'none';
                    install_section.style.display = 'block';
                    dismiss.style.display = 'block';
                });
            }

            // install button
            if (addBtn) {
                addBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    // Show the prompt
                    deferredPrompt.prompt();
                    // Wait for the user to respond to the prompt
                    deferredPrompt.userChoice.then((choiceResult) => {
                        if (choiceResult.outcome === 'accepted') {
                            // hide our user interface that shows our A2HS button
                            section.style.display = 'none';
                        }
                        deferredPrompt = null;
                    });
                });
            }
        }
    });
}
