import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../static/src/js/session_checker.js", import.meta.url), "utf8")
    .replace(/^import .*;\r?$/gm, "");
const flush = () => new Promise((resolve) => setImmediate(resolve));

function setup(responses) {
    const calls = [], timers = [], redirects = [];
    let service;
    vm.runInNewContext(source, {
        registry: { category: () => ({ add: (name, value) => { service = value; } }) },
        window: {
            setTimeout: (callback) => timers.push(callback),
            location: { replace: (url) => redirects.push(url) },
        },
        rpc: async (path) => {
            calls.push(path);
            const result = responses.shift();
            if (result instanceof Error) throw result;
            return await result;
        },
    });
    service.start();
    return { calls, timers, redirects };
}

test("checks immediately and waits for slow requests before scheduling", async () => {
    let resolve;
    const client = setup([new Promise((done) => { resolve = done; })]);
    assert.deepEqual(client.calls, ["/single_session/check"]);
    assert.equal(client.timers.length, 0);
    resolve({ logout: false });
    await flush();
    assert.equal(client.timers.length, 1);
});

test("temporary failures retry and an invalid session stops the loop", async () => {
    const client = setup([new Error("offline"), { logout: true }]);
    await flush();
    assert.equal(client.redirects.length, 0);
    client.timers.shift()();
    await flush();
    assert.deepEqual(client.redirects, ["/web/login"]);
    assert.equal(client.timers.length, 0);
});

test("server session-expired errors redirect immediately", async () => {
    const error = new Error("expired");
    error.data = { name: "odoo.http.SessionExpiredException" };
    const client = setup([error]);
    await flush();
    assert.deepEqual(client.redirects, ["/web/login"]);
    assert.equal(client.timers.length, 0);
});
