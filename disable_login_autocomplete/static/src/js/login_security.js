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
        alert("Paste disabled for security");
    });

    /*
    Disable right click on login page
    */
    loginForm.addEventListener("contextmenu", function (e) {
        e.preventDefault();
    });

    return true;
}

/*
Wait until OWL renders login form
*/
const interval = setInterval(() => {
    if (applyLoginSecurity()) {
        clearInterval(interval);
    }
}, 300);