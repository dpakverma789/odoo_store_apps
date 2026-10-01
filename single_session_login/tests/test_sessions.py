from odoo.tests.common import Opener

from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSingleSession(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env, login="single_session_test", password="session-test-password"
        )

    def rpc(self, browser, path, params=None):
        self.opener = browser
        response = browser.post(
            self.base_url() + path,
            json={"jsonrpc": "2.0", "method": "call", "params": params or {}, "id": 1},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def login(self):
        browser = Opener(self)
        self.addCleanup(browser.close)
        result = self.rpc(browser, "/web/session/authenticate", {
            "db": self.env.cr.dbname,
            "login": self.user.login,
            "password": "session-test-password",
        })
        self.assertNotIn("error", result)
        self.assertEqual(result["result"]["uid"], self.user.id)
        return browser

    def check(self, browser, logout=False):
        result = self.rpc(browser, "/single_session/check")
        self.assertNotIn("error", result)
        self.assertEqual(result["result"], {"logout": logout})

    def test_latest_login_wins(self):
        first = self.login()
        self.check(first)
        second = self.login()
        self.check(second)
        self.check(first, logout=True)
        self.check(second)

    def test_replaced_session_blocked_without_checker(self):
        first = self.login()
        self.login()
        result = self.rpc(first, "/web/session/get_session_info")
        self.assertEqual(result["error"]["data"]["name"], "odoo.http.SessionExpiredException")

    def test_replaced_session_cannot_bootstrap_backend(self):
        first = self.login()
        self.login()
        self.opener = first
        response = first.get(self.base_url() + "/odoo", allow_redirects=False, timeout=20)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].startswith("/web/login"))

    def test_exempt_user_keeps_both_sessions(self):
        self.user.allow_multiple_sessions = True
        self.env.flush_all()
        first = self.login()
        second = self.login()
        self.check(first)
        self.check(second)

    def test_failed_login_keeps_current_session(self):
        first = self.login()
        with Opener(self) as second:
            result = self.rpc(second, "/web/session/authenticate", {
                "db": self.env.cr.dbname,
                "login": self.user.login,
                "password": "incorrect-password",
            })
        self.assertIn("error", result)
        self.check(first)

    def test_noninteractive_login_keeps_current_session(self):
        first = self.login()
        self.env["res.users"].authenticate({
            "type": "password", "login": self.user.login,
            "password": "session-test-password",
        }, {"interactive": False})
        self.check(first)

    def test_session_fields_are_admin_only(self):
        fields = self.user.with_user(self.user).fields_get()
        self.assertNotIn("allow_multiple_sessions", fields)
        self.assertNotIn("session_uuid", fields)

    def test_mfa_only_claims_session_after_second_factor(self):
        if "totp_secret" not in self.user._fields:
            self.skipTest("auth_totp is not installed")
        from lxml import html
        from passlib.totp import TOTP

        secret = "JBSWY3DPEHPK3PXP"
        self.user.sudo().totp_secret = secret
        self.user.session_uuid = "previous-session"
        self.env.flush_all()
        with Opener(self) as browser:
            result = self.rpc(browser, "/web/session/authenticate", {
                "db": self.env.cr.dbname,
                "login": self.user.login,
                "password": "session-test-password",
            })
            self.assertNotIn("error", result)
            self.assertFalse(result["result"]["uid"])
            self.user.invalidate_recordset(["session_uuid"])
            self.assertEqual(self.user.session_uuid, "previous-session")
            page = browser.get(self.base_url() + "/web/login/totp", timeout=20)
            page.raise_for_status()
            csrf = html.fromstring(page.content).xpath('//input[@name="csrf_token"]/@value')[0]
            invalid = browser.post(
                self.base_url() + "/web/login/totp",
                data={"csrf_token": csrf, "totp_token": "invalid"}, timeout=20,
            )
            self.assertEqual(invalid.status_code, 200)
            self.user.invalidate_recordset(["session_uuid"])
            self.assertEqual(self.user.session_uuid, "previous-session")
            response = browser.post(
                self.base_url() + "/web/login/totp",
                data={"csrf_token": csrf, "totp_token": TOTP(secret).generate().token},
                allow_redirects=False, timeout=20,
            )
            self.assertEqual(response.status_code, 303)
            self.check(browser)
            self.user.invalidate_recordset(["session_uuid"])
            self.assertNotEqual(self.user.session_uuid, "previous-session")
