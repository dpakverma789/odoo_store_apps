/** @odoo-module **/

function applyLoginSecurity() {

    const loginForm = document.querySelector('form[action*="/web/login"]');
    const passwordInput = document.querySelector('input[name="password"]');

    if (!loginForm || !passwordInput) {
        return false;
    }

    /*
    Disable paste in password
    */
    passwordInput.addEventListener("paste", function (e) {
        e.preventDefault();
    });

    /*
    Disable right click on entire login page
    */
    document.addEventListener("contextmenu", function (e) {
        e.preventDefault();
    });

    return true;
}

/*
Wait until Odoo OWL renders login page
*/
const interval = setInterval(() => {
    if (applyLoginSecurity()) {
        clearInterval(interval);
    }
}, 300);