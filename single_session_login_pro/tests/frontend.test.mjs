import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(new URL("../static/src/js/session_checker.js", import.meta.url), "utf8")
    .replace(/^import .*;\r?$/gm, "")
    .replace("export const safeReasons", "const safeReasons");
const flush = () => new Promise((resolve) => setImmediate(resolve));

function setup(responses = []) {
    const calls = [], timers = [], dialogs = [], redirects = [];
    const listeners = {};
    let service, now = 100000, running = 0, maximum = 0;
    const context = {
        registry: { category: () => ({ add: (name, value) => { service = value; } }) },
        ConfirmationDialog: class {},
        _t: (value, arg) => value.replace("%s", arg),
        Date: { now: () => now },
        window: {
            addEventListener: (name, callback) => { listeners[name] = callback; },
            setTimeout: (callback) => timers.push(callback),
            location: { replace: (url) => redirects.push(url) },
        },
        rpc: async (path) => {
            calls.push(path);
            maximum = Math.max(maximum, ++running);
            try {
                const response = responses.shift() ?? { logout: false };
                if (response instanceof Error) throw response;
                return await response;
            } finally { running--; }
        },
    };
    vm.runInNewContext(source, context);
    service.start({}, { dialog: { add: (component, props) => {
        const entry = { props, closed: false };
        dialogs.push(entry);
        return () => { entry.closed = true; };
    } } });
    return {
        calls, timers, dialogs, redirects, responses,
        maximum: () => maximum,
        activity: () => listeners.pointerdown({ isTrusted: true }),
        async tick(ms = 5000) { now += ms; assert.ok(timers.length); timers.shift()(); await flush(); },
    };
}

test("passive checks never send activity; real activity is throttled", async () => {
    const client = setup(); await flush();
    await client.tick();
    assert.deepEqual(client.calls, ["/single_session/check", "/single_session/check"]);
    client.activity(); await client.tick();
    assert.equal(client.calls.at(-1), "/single_session/activity");
    client.activity(); await client.tick();
    assert.equal(client.calls.at(-1), "/single_session/check");
    await client.tick(30000);
    assert.equal(client.calls.at(-1), "/single_session/activity");
});

test("slow checks never overlap", async () => {
    let resolve;
    const client = setup([new Promise((done) => { resolve = done; })]);
    await flush();
    assert.equal(client.timers.length, 0);
    resolve({ logout: false }); await flush();
    assert.equal(client.timers.length, 1);
    await client.tick();
    assert.equal(client.maximum(), 1);
});

test("temporary failure retries without logout", async () => {
    const client = setup([new Error("offline")]); await flush();
    assert.equal(client.redirects.length, 0);
    await client.tick();
    assert.equal(client.calls.length, 2);
});

test("one warning dialog; Stay Logged In uses activity endpoint", async () => {
    const warning = { logout: false, warning: true, seconds_remaining: 110 };
    const client = setup([warning, warning, { logout: false, warning: false }]);
    await flush(); await client.tick();
    assert.equal(client.dialogs.length, 1);
    assert.match(client.dialogs[0].props.body, /2 minutes/);
    await client.dialogs[0].props.confirm();
    assert.equal(client.calls.at(-1), "/single_session/activity");
});

test("failed Stay Logged In keeps warning open", async () => {
    const client = setup([{ logout: false, warning: true, seconds_remaining: 60 }, new Error("offline")]);
    await flush();
    assert.equal(await client.dialogs[0].props.confirm(), false);
    assert.equal(client.redirects.length, 0);
});

test("recent activity suppresses stale warning", async () => {
    const client = setup(); await flush();
    client.activity(); await client.tick();
    client.activity();
    client.responses.push({ logout: false, warning: true, seconds_remaining: 90 });
    await client.tick();
    assert.equal(client.dialogs.length, 0);
});

test("safe logout reason redirects and stops polling", async () => {
    const client = setup([{ logout: true, reason: "admin_revoked" }]); await flush();
    assert.deepEqual(client.redirects, ["/web/login?single_session_reason=admin_revoked"]);
    assert.equal(client.timers.length, 0);
    const unknown = setup([{ logout: true, reason: "<script>" }]); await flush();
    assert.deepEqual(unknown.redirects, ["/web/login"]);
});

test("Sign Out Now calls logout endpoint", async () => {
    const client = setup([{ logout: false, warning: true, seconds_remaining: 60 }, { logout: true }]);
    await flush(); await client.dialogs[0].props.cancel();
    assert.equal(client.calls.at(-1), "/single_session/logout");
    assert.deepEqual(client.redirects, ["/web/login"]);
});
