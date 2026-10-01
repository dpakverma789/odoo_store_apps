/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export const safeReasons = new Set([
    "replaced_by_new_login", "new_login_rejected", "idle_timeout",
    "admin_revoked", "session_invalidated",
]);

// Replaces the free asset in the bundle: exactly one checker service/loop.
registry.category("services").add("single_session_checker", {
    dependencies: ["dialog"],
    start(env, { dialog }) {
        let dirty = false;
        let lastActivitySent = 0;
        let closeWarning;
        let stopped = false;
        let queue = Promise.resolve();
        let warningDismissed = false;

        function redirect(reason) {
            stopped = true;
            const suffix = safeReasons.has(reason) ? `?single_session_reason=${reason}` : "";
            window.location.replace(`/web/login${suffix}`);
        }

        function activity(event) {
            // Opening the dialog, polling, and synthetic DOM events are not activity.
            if (event.isTrusted && !closeWarning) {
                dirty = true;
                warningDismissed = false;
            }
        }
        for (const name of ["pointerdown", "keydown", "input", "change"]) {
            window.addEventListener(name, activity, { passive: true, capture: true });
        }

        function hideWarning() {
            if (closeWarning) {
                const close = closeWarning;
                closeWarning = undefined;
                close();
            }
        }

        function send(path) {
            // Serialize checker, activity, and explicit dialog actions together.
            const pending = queue.then(() => stopped ? undefined : rpc(path, {}, { silent: true }));
            queue = pending.catch(() => {});
            return pending;
        }

        async function stayLoggedIn() {
            try {
                const result = await send("/single_session/activity");
                if (result?.logout) {
                    redirect(result.reason);
                    return;
                }
                lastActivitySent = Date.now();
                dirty = false;
                warningDismissed = false;
                closeWarning = undefined;
            } catch {
                // Keep the dialog available for retry; never promise an extension
                // when the server has not acknowledged activity.
                return false;
            }
        }

        async function signOut() {
            try {
                const result = await send("/single_session/logout");
                if (result?.logout) {
                    redirect();
                }
            } catch {
                return false;
            }
        }

        function handle(result) {
            if (!result) {
                return;
            }
            if (result.logout) {
                redirect(result.reason);
            } else if (!result.warning) {
                hideWarning();
                warningDismissed = false;
            } else if (!closeWarning && !warningDismissed && !dirty) {
                closeWarning = dialog.add(ConfirmationDialog, {
                    title: _t("Session Expiring Soon"),
                    body: _t("Your session will expire in approximately %s minutes due to inactivity.",
                        Math.max(1, Math.ceil(result.seconds_remaining / 60))),
                    confirmLabel: _t("Stay Logged In"),
                    cancelLabel: _t("Sign Out Now"),
                    confirm: stayLoggedIn,
                    cancel: signOut,
                    dismiss: () => {
                        warningDismissed = true;
                        closeWarning = undefined;
                    },
                });
            }
        }

        async function checkSession() {
            try {
                // A dirty activity report goes first, avoiding an obsolete warning.
                const touch = dirty && Date.now() - lastActivitySent >= 30000;
                if (touch) {
                    dirty = false;
                }
                let result;
                try {
                    result = await send(touch ? "/single_session/activity" : "/single_session/check");
                } catch (error) {
                    if (touch) {
                        dirty = true;
                    }
                    throw error;
                }
                if (touch && !result?.logout) {
                    lastActivitySent = Date.now();
                }
                handle(result);
            } catch (error) {
                if (error.data?.name === "odoo.http.SessionExpiredException") {
                    // The public checker retrieves the reason saved by enforcement.
                    try {
                        handle(await send("/single_session/check"));
                    } catch {
                        // Retry on the next tick if the connection is unavailable.
                    }
                }
            }
            if (!stopped) {
                window.setTimeout(checkSession, 5000);
            }
        }
        checkSession();
    },
});
