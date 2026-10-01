from odoo import http, _
from odoo.http import request
from odoo.addons.single_session_login.controllers.session_check import SingleSessionCheck
from odoo.addons.web.controllers.home import Home


def logout_message(reason):
    return {
        "replaced_by_new_login": _("You were signed out because your account was logged in elsewhere."),
        "new_login_rejected": _("Your account already has an active session. Sign out from the other session first, or contact your administrator."),
        "idle_timeout": _("Your session expired due to inactivity. Please sign in again to continue."),
        "admin_revoked": _("Your session was terminated by an administrator. Please sign in again if you still require access."),
        "session_invalidated": _("Your session is no longer valid. Please sign in again."),
    }.get(reason)


def logout_title(reason):
    if not logout_message(reason):
        return None
    return {
        "new_login_rejected": _("Login Not Allowed"),
        "idle_timeout": _("Session Expired"),
    }.get(reason, _("Session Ended"))


class ProSessionCheck(SingleSessionCheck):
    @http.route(auth="public", readonly=False)
    def check(self):
        # Public allows an already-logged-out browser to retrieve its safe reason.
        # Never accept a user or session identifier from the caller.
        if not request.session.uid:
            reason = request.session.get("single_session_reason", "session_invalidated")
            return {"logout": True, "reason": reason if logout_message(reason) else "session_invalidated"}
        return self._result(request.env["user.session"].sudo()._check_current())

    def _result(self, result):
        if result["logout"]:
            request.env["ir.http"]._single_session_logout(result["reason"])
        return result

    @http.route("/single_session/activity", type="jsonrpc", auth="user", readonly=False)
    def activity(self):
        return self._result(request.env["user.session"].sudo()._check_current(touch=True))

    @http.route("/single_session/logout", type="jsonrpc", auth="user", readonly=False)
    def logout(self):
        request.env["user.session"].sudo()._current()._end("user_logout")
        request.session.logout(keep_db=True)
        return {"logout": True}


class ProHome(Home):
    @http.route()
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)
        if response.is_qweb:
            reason = kw.get("single_session_reason") or request.session.get("single_session_reason")
            response.qcontext["single_session_message"] = logout_message(reason)
            response.qcontext["single_session_title"] = logout_title(reason)
        return response
