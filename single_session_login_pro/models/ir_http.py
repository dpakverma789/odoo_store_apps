import json

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _single_session_logout(cls, reason):
        request.session.logout(keep_db=True)
        request.session["single_session_reason"] = reason

    @classmethod
    def _single_session_block(cls, endpoint, reason):
        cls._single_session_logout(reason)
        if endpoint.routing["type"] == "http":
            return request.redirect("/web/login?single_session_reason=" + reason, 303)
        # Return normally so expiry/audit writes commit. _post_dispatch replaces
        # the JSON envelope with Odoo's standard session-expired error contract.
        request._single_session_blocked = reason
        return None

    @classmethod
    def _dispatch(cls, endpoint):
        sessions = request.env["user.session"].sudo()
        path = request.httprequest.path
        control = path in {"/single_session/check", "/single_session/activity", "/single_session/logout"}
        logout = path in {"/web/session/logout", "/web/session/destroy"}
        bearer = endpoint.routing["auth"] == "bearer" and request.httprequest.headers.get("Authorization", "").startswith("Bearer ")
        if logout and request.session.uid:
            sessions._current()._end("user_logout")
        elif request.session.uid and not control and not bearer and endpoint.routing["auth"] != "none":
            # Only explicit mutation/button routes count here. Reads, bus polling,
            # session checks, assets and other passive traffic never extend idle time.
            application_action = path.startswith("/web/dataset/call_button") or (
                path.startswith("/web/dataset/call_kw")
                and request.params.get("method") in {"create", "write", "unlink", "web_save"}
            )
            state = sessions._check_current(touch=application_action)
            if state["logout"]:
                return cls._single_session_block(endpoint, state["reason"])
        result = super()._dispatch(endpoint)
        # Session.finalize has now run, either in password login or an MFA
        # controller. A partial password-only MFA session has no uid.
        if request.session.uid and request.session.get("single_session_pending_uid") == request.session.uid:
            record = sessions._activate_current()
            if record and record.status != "active":
                reason = record.end_reason
                cls._single_session_logout(reason)
                if endpoint.routing["type"] == "http":
                    return request.redirect("/web/login?single_session_reason=" + reason, 303)
                return {"uid": False, "single_session_reason": reason}
        return result

    @classmethod
    def _post_dispatch(cls, response):
        if getattr(request, "_single_session_blocked", None):
            response.set_data(json.dumps({
                "jsonrpc": "2.0", "id": getattr(request.dispatcher, "request_id", None),
                "error": {"code": 100, "message": "Odoo Session Expired", "data": {
                    "name": "odoo.http.SessionExpiredException", "message": "Session expired",
                    "arguments": [], "context": {},
                }},
            }))
            response.headers["Content-Type"] = "application/json"
        return super()._post_dispatch(response)
