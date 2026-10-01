from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch

import odoo
from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import Opener
from odoo.addons.single_session_login.tests.test_sessions import TestSingleSession


@tagged("post_install", "-at_install")
class TestProSessions(TestSingleSession):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sessions = cls.env["user.session"].sudo().with_context(active_test=False)

    def setting(self, name, value):
        self.env["ir.config_parameter"].sudo().set_param("single_session_login_pro." + name, value)

    def check(self, browser, logout=False, reason=None):
        result = self.rpc(browser, "/single_session/check")
        self.assertNotIn("error", result)
        self.assertEqual(result["result"]["logout"], logout)
        if reason:
            self.assertEqual(result["result"]["reason"], reason)
        return result["result"]

    def rows(self):
        self.env.invalidate_all()
        return self.sessions.search([("user_id", "=", self.user.id)])

    def test_free_latest_login_wins(self):
        super().test_latest_login_wins()

    def test_free_exempt_sessions(self):
        super().test_exempt_user_keeps_both_sessions()

    def test_free_failed_login(self):
        super().test_failed_login_keeps_current_session()

    def test_free_noninteractive_login(self):
        super().test_noninteractive_login_keeps_current_session()

    def test_free_admin_fields(self):
        super().test_session_fields_are_admin_only()

    def test_free_mfa_completion(self):
        super().test_mfa_only_claims_session_after_second_factor()

    def test_register_replace_history(self):
        first = self.login()
        self.assertEqual(self.rows().status, "active")
        second = self.login()
        self.check(first, True, "replaced_by_new_login")
        self.check(second)
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows.filtered(lambda row: row.status == "active")), 1)
        ended = rows.filtered(lambda row: row.status == "ended")
        self.assertEqual(ended.end_reason, "replaced_by_new_login")
        end = ended.end_datetime
        self.check(first, True, "replaced_by_new_login")
        self.assertEqual(ended.end_datetime, end)
        self.assertEqual(len(self.rows()), 2)

    def test_reject_preserves_existing(self):
        self.setting("conflict_policy", "reject_new")
        first = self.login()
        with Opener(self) as second:
            result = self.rpc(second, "/web/session/authenticate", {
                "db": self.env.cr.dbname, "login": self.user.login,
                "password": "session-test-password",
            })
            self.assertEqual(result["result"]["single_session_reason"], "new_login_rejected")
            self.assertFalse(result["result"]["uid"])
            self.check(second, True, "new_login_rejected")
        self.check(first)
        self.assertEqual(len(self.rows().filtered(lambda row: row.status == "rejected")), 1)

    def test_reject_web_login_form_message(self):
        from lxml import html

        self.setting("conflict_policy", "reject_new")
        first = self.login()
        with Opener(self) as second:
            self.opener = second
            page = second.get(self.base_url() + "/web/login", timeout=20)
            csrf = html.fromstring(page.content).xpath('//input[@name="csrf_token"]/@value')[0]
            response = second.post(self.base_url() + "/web/login", data={
                "csrf_token": csrf, "login": self.user.login,
                "password": "session-test-password",
            }, timeout=20)
            self.assertIn("Login Not Allowed", response.text)
            self.assertIn("Your account already has an active session.", response.text)
            self.assertIn("Sign out from the other session first", response.text)
            self.assertNotIn("Wrong login/password", response.text)
        self.check(first)

    def test_mfa_reject_only_after_second_factor(self):
        if "totp_secret" not in self.user._fields:
            self.skipTest("auth_totp is not installed")
        from lxml import html
        from passlib.totp import TOTP

        self.setting("conflict_policy", "reject_new")
        active = self.sessions._register_session(self.user.sudo(), "existing-mfa-session")
        secret = "JBSWY3DPEHPK3PXP"
        self.user.sudo().totp_secret = secret
        self.env.flush_all()
        with Opener(self) as browser:
            result = self.rpc(browser, "/web/session/authenticate", {
                "db": self.env.cr.dbname, "login": self.user.login,
                "password": "session-test-password",
            })
            self.assertFalse(result["result"]["uid"])
            self.assertEqual(self.rows(), active)
            self.assertEqual(active.status, "active")
            page = browser.get(self.base_url() + "/web/login/totp", timeout=20)
            csrf = html.fromstring(page.content).xpath('//input[@name="csrf_token"]/@value')[0]
            browser.post(self.base_url() + "/web/login/totp", data={
                "csrf_token": csrf, "totp_token": "invalid",
            }, timeout=20)
            self.assertEqual(self.rows(), active)
            self.assertEqual(self.user.session_uuid, "existing-mfa-session")
            response = browser.post(self.base_url() + "/web/login/totp", data={
                "csrf_token": csrf, "totp_token": TOTP(secret).generate().token,
            }, timeout=20)
            self.assertIn("Your account already has an active session.", response.text)
            self.assertEqual(len(self.rows()), 2)
            self.assertEqual(active.status, "active")
            self.assertEqual(self.user.session_uuid, "existing-mfa-session")

    def test_browser_reject_login_message(self):
        self.setting("conflict_policy", "reject_new")
        first = self.login()
        self.browser_js("/web/login", """
            (async () => {
                const form = document.querySelector('form.oe_login_form');
                if (!form) throw new Error('Login form missing');
                const data = new FormData(form);
                data.set('login', 'single_session_test');
                data.set('password', 'session-test-password');
                const response = await fetch('/web/login', {method: 'POST', body: data});
                const page = new DOMParser().parseFromString(await response.text(), 'text/html');
                const message = page.querySelector('[role="status"]')?.textContent || '';
                if (!message.includes('Login Not Allowed') ||
                    !message.includes('Your account already has an active session.') ||
                    !message.includes('Sign out from the other session first')) {
                    throw new Error('Specific rejection message missing: ' + message);
                }
                if (!page.querySelector('form.oe_login_form') ||
                    page.body.textContent.includes('Wrong login/password')) {
                    throw new Error('Rejected login did not return the usable login form');
                }
                console.log('test successful');
            })();
        """, timeout=60)
        self.check(first)

    def test_browser_replace_login(self):
        first = self.login()
        self.browser_js("/web/login", """
            (async () => {
                const data = new FormData(document.querySelector('form.oe_login_form'));
                data.set('login', 'single_session_test');
                data.set('password', 'session-test-password');
                const response = await fetch('/web/login', {method: 'POST', body: data});
                if (!response.ok || new URL(response.url).pathname !== '/odoo') {
                    throw new Error('Successful form login did not reach the backend');
                }
                const check = await fetch('/single_session/check', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}, id: 1}),
                });
                const state = await check.json();
                if (state.error || state.result.logout) throw new Error('New session is invalid');
                console.log('test successful');
            })();
        """, timeout=60)
        self.check(first, True, "replaced_by_new_login")

    def test_replaced_session_blocked_without_checker(self):
        first = self.login()
        self.login()
        result = self.rpc(first, "/web/session/get_session_info")
        self.assertEqual(result["error"]["data"]["name"], "odoo.http.SessionExpiredException")
        self.check(first, True, "replaced_by_new_login")

    def test_activity_and_checker(self):
        browser = self.login()
        row = self.rows()
        old = fields.Datetime.now() - timedelta(minutes=5)
        row.last_activity_datetime = old
        self.env.flush_all()
        self.check(browser)
        self.assertEqual(self.rows().last_activity_datetime, old)
        result = self.rpc(browser, "/single_session/activity")["result"]
        self.assertFalse(result["logout"])
        self.assertGreater(self.rows().last_activity_datetime, old)

    def test_warning_stay_and_expiry(self):
        self.setting("idle_enabled", True)
        browser = self.login()
        row = self.rows()
        row.last_activity_datetime = fields.Datetime.now() - timedelta(minutes=29)
        self.env.flush_all()
        self.assertTrue(self.check(browser)["warning"])
        result = self.rpc(browser, "/single_session/activity")["result"]
        self.assertFalse(result["warning"])
        row.last_activity_datetime = fields.Datetime.now() - timedelta(minutes=31)
        self.env.flush_all()
        self.check(browser, True, "idle_timeout")
        self.assertEqual(self.rows().status, "expired")

    def test_idle_blocked_without_checker(self):
        self.setting("idle_enabled", True)
        browser = self.login()
        self.rows().last_activity_datetime = fields.Datetime.now() - timedelta(minutes=31)
        self.env.flush_all()
        result = self.rpc(browser, "/web/session/get_session_info")
        self.assertIn("error", result)
        self.assertEqual(self.rows().end_reason, "idle_timeout")

    def test_expired_session_cannot_revive(self):
        self.setting("idle_enabled", True)
        browser = self.login()
        self.rows().last_activity_datetime = fields.Datetime.now() - timedelta(minutes=31)
        self.env.flush_all()
        result = self.rpc(browser, "/single_session/activity")["result"]
        self.assertEqual(result, {"logout": True, "reason": "idle_timeout"})

    def test_admin_revoke_and_access(self):
        browser = self.login()
        row = self.rows()
        with self.assertRaises(AccessError):
            row.with_user(self.user).read(["session_reference"])
        with self.assertRaises(AccessError):
            row.with_user(self.user).action_end_session()
        result = self.rpc(browser, "/web/dataset/call_button", {
            "model": "user.session", "method": "action_end_session",
            "args": [[row.id]], "kwargs": {},
        })
        self.assertEqual(result["error"]["data"]["name"], "odoo.exceptions.AccessError")
        self.assertEqual(self.rows().status, "active")
        admin = self.env.ref("base.user_admin")
        row.with_user(admin).read(["status"])
        row.with_user(admin).action_end_session()
        self.env.flush_all()
        result = self.rpc(browser, "/web/session/get_session_info")
        self.assertIn("error", result)
        self.check(browser, True, "admin_revoked")
        self.assertEqual(self.rows().revoked_by, admin)

    def test_regular_logout_history(self):
        browser = self.login()
        self.rpc(browser, "/web/session/destroy")
        self.assertEqual(self.rows().end_reason, "user_logout")

    def test_passive_dataset_and_public_routes(self):
        browser = self.login()
        old = fields.Datetime.now() - timedelta(minutes=5)
        self.rows().last_activity_datetime = old
        self.env.flush_all()
        result = self.rpc(browser, "/web/dataset/call_kw/res.users/read", {
            "model": "res.users", "method": "read",
            "args": [[self.user.id], ["name"]], "kwargs": {},
        })
        self.assertNotIn("error", result)
        self.assertEqual(self.rows().last_activity_datetime, old)
        self.opener = browser
        health = browser.get(self.base_url() + "/web/health", timeout=20)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(self.rows().last_activity_datetime, old)

    def test_retention(self):
        now = fields.Datetime.now()
        def create(status, days):
            return self.sessions.create({
                "user_id": self.user.id, "session_reference": uuid4().hex,
                "status": status, "active": status == "active",
                "login_datetime": now - timedelta(days=days + 1),
                "last_activity_datetime": now - timedelta(days=days),
                "end_datetime": now - timedelta(days=days) if status != "active" else False,
            })
        old = create("ended", 40) | create("expired", 40) | create("rejected", 40)
        inconsistent = create("ended", 40)
        inconsistent.active = True
        keep = create("ended", 2) | create("active", 40) | inconsistent
        self.sessions._cron_cleanup()
        self.assertFalse(old.exists())
        self.assertEqual(len(keep.exists()), 3)
        self.setting("retention_days", 0)
        indefinite = create("ended", 50)
        self.sessions._cron_cleanup()
        self.assertTrue(indefinite.exists())

    def test_invalid_settings(self):
        for values in [{"session_idle_minutes": 0}, {"session_warning_minutes": -1},
                       {"session_warning_minutes": 30}, {"session_retention_days": -1}]:
            with self.assertRaises(ValidationError), self.env.cr.savepoint():
                self.env["res.config.settings"].create(values)

    def test_safe_login_message(self):
        with Opener(self) as browser:
            self.opener = browser
            response = browser.get(self.base_url() + "/web/login?single_session_reason=admin_revoked", timeout=20)
            self.assertIn("terminated by an administrator", response.text)
            response = browser.get(self.base_url() + "/web/login?single_session_reason=UNTRUSTED_REASON", timeout=20)
            self.assertNotIn("UNTRUSTED_REASON", response.text)

    def test_browser_dashboard_and_warning(self):
        self.setting("idle_enabled", True)
        original = self.authenticate

        def authenticated_fixture(*args, **kwargs):
            # HttpCase.authenticate creates a native session directly (not a
            # browser login). Attach its corresponding registry fixture too.
            session = original(*args, **kwargs)
            token = uuid4().hex
            row = self.sessions._register_session(self.env["res.users"].browse(session.uid), token)
            row.last_activity_datetime = fields.Datetime.now() - timedelta(minutes=29)
            self.env.flush_all()
            self.assertTrue(self.sessions._settings()["enabled"])
            session.update(single_session_uuid=token, single_session_pro_registered=True)
            odoo.http.root.session_store.save(session)
            return session

        with patch.object(self, "authenticate", authenticated_fixture):
            self.browser_js("/odoo/action-single_session_login_pro.action_active_sessions", """
                (async () => {
                    const wait = async (predicate) => {
                        for (let i = 0; i < 150; i++) {
                            if (predicate()) return;
                            await new Promise(resolve => setTimeout(resolve, 100));
                        }
                        throw new Error('Expected UI state was not displayed');
                    };
                    await wait(() => document.querySelector('.o_list_view'));
                    const response = await fetch('/single_session/check', {
                        method: 'POST', headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}, id: 1}),
                    });
                    const state = await response.json();
                    if (!state.result?.warning) throw new Error('Expected server warning: ' + JSON.stringify(state));
                    await wait(() => document.body.textContent.includes('Session Expiring Soon'));
                    const button = [...document.querySelectorAll('.modal button')]
                        .find(button => button.textContent.includes('Stay Logged In'));
                    if (!button) throw new Error('Stay Logged In button missing');
                    button.click();
                    await wait(() => !document.body.textContent.includes('Session Expiring Soon'));
                    console.log('test successful');
                })();
            """, login="admin", timeout=90)
