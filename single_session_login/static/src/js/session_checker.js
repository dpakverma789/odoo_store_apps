/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

registry.category("services").add("single_session_checker", {
    start() {
        async function checkSession() {
            try {
                const result = await rpc("/single_session/check", {}, { silent: true });
                if (result?.logout) {
                    window.location.replace("/web/login");
                    return;
                }
            } catch (error) {
                if (error.data?.name === "odoo.http.SessionExpiredException") {
                    window.location.replace("/web/login");
                    return;
                }
                // Retry temporary connection failures on the next check.
            }
            // Schedule after completion so slow requests never overlap.
            window.setTimeout(checkSession, 5000);
        }
        checkSession();
    },
});
