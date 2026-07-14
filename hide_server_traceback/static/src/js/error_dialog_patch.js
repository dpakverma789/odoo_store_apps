/** @odoo-module **/

const CUSTOM_MESSAGE =
    "Something went wrong. Please contact your administrator.";

const observer = new MutationObserver(() => {

    document.querySelectorAll(".o_error_dialog").forEach((dialog) => {

        // Already processed
        if (dialog.dataset.hideServerTraceback === "1") {
            return;
        }

        // Only process actual Odoo Server Error dialogs
        const technicalButton = [...dialog.querySelectorAll(".btn-link")]
            .find(btn =>
                btn.textContent.toLowerCase().includes("technical")
            );

        if (!technicalButton) {
            return;
        }

        dialog.dataset.hideServerTraceback = "1";

        // ----------------------------
        // Dialog title
        // ----------------------------
        const title = dialog.querySelector(".modal-title");

        if (title) {
            title.textContent = "Odoo Server Error";
        }

        // ----------------------------
        // Dialog body
        // ----------------------------
        const body = dialog.querySelector(".modal-body");

        if (!body) {
            return;
        }

        // Remove technical details section
        body.querySelectorAll(
            ".o_error_detail, .o_error_debug, pre, code"
        ).forEach(el => el.remove());

        // Remove "See technical details"
        technicalButton.remove();

        // Replace only the default Odoo message
        const firstParagraph = body.querySelector("p");

        if (
            firstParagraph &&
            firstParagraph.textContent.toLowerCase().includes("something went wrong")
        ) {
            firstParagraph.textContent = CUSTOM_MESSAGE;
        }

    });

});

function startObserver() {

    const target = document.body || document.documentElement;

    if (!target) {
        requestAnimationFrame(startObserver);
        return;
    }

    observer.observe(target, {
        childList: true,
        subtree: true,
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startObserver);
} else {
    startObserver();
}