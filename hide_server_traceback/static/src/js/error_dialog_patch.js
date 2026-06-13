/** @odoo-module **/

console.log("Hide Server Error Loaded");

document.addEventListener("click", () => {
    setTimeout(() => {

        document.querySelectorAll(".modal").forEach((modal) => {

            const title = modal.querySelector(".modal-title");
            if (title) {
                title.textContent = "Odoo Server Error";
            }

            const body = modal.querySelector(".modal-body");
            if (body) {
                body.textContent =
                    "Something went wrong. Please contact administrator.";
            }

        });

    }, 100);
});