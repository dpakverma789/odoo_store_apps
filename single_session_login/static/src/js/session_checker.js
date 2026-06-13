/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

console.log("Single Session Checker Loaded");

setInterval(async () => {
    console.log("Checking session...");

    try {

        const result = await rpc("/single_session/check", {});
        console.log("Session Check Response:", result);
        
        if (result && result.logout) {
            console.warn("Session invalidated. Redirecting...");
            window.location.replace("/web/login");
        }

    } catch (error) {

        console.error("Single Session Error", error);
    }

}, 5000); // 5 seconds