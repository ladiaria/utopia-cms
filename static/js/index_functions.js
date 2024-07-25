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
