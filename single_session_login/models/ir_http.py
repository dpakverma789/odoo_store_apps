import json

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _single_session_logout(cls, reason=None):
        request.session.logout(keep_db=True)
        if reason:
            request.session["single_session_reason"] = reason

    @classmethod
    def _single_session_block(cls, endpoint, reason=None):
        cls._single_session_logout(reason)
        if endpoint.routing["type"] == "http":
            suffix = "?single_session_reason=" + reason if reason else ""
            return request.redirect("/web/login" + suffix, 303)
        # Return normally so session termination and audit writes commit.
        request._single_session_blocked = True
        return None

    @classmethod
    def _single_session_request_state(cls):
        return request.env["res.users"].sudo().browse(request.session.uid)._single_session_validate()

    @classmethod
    def _single_session_record_logout(cls):
        pass

    @classmethod
    def _single_session_complete_pending(cls):
        return cls._single_session_request_state()

    @classmethod
    def _dispatch(cls, endpoint):
        # Odoo can retry dispatch after a PostgreSQL serialization failure.
        request._single_session_blocked = False
        path = request.httprequest.path
        control = path in {"/single_session/check", "/single_session/activity", "/single_session/logout"}
        logout = path in {"/web/session/logout", "/web/session/destroy"}
        bearer = endpoint.routing["auth"] == "bearer" and request.httprequest.headers.get("Authorization", "").startswith("Bearer ")
        # Odoo's backend bootstrap deliberately uses auth='none'. Only these
        # known authenticated pages are included; login and public APIs are not.
        backend = path in {"/web", "/odoo"} or path.startswith(("/odoo/", "/scoped_app/"))
        if request.session.uid and not bearer:
            if logout:
                cls._single_session_record_logout()
            elif not control and (endpoint.routing["auth"] != "none" or backend):
                state = cls._single_session_request_state()
                if state["logout"]:
                    return cls._single_session_block(endpoint, state.get("reason"))
        result = super()._dispatch(endpoint)
        # Finalize a pending login only after Odoo has completed authentication,
        # including MFA. A password-only MFA session has no uid.
        if not bearer and request.session.uid and request.session.get("single_session_pending_uid") == request.session.uid:
            state = cls._single_session_complete_pending()
            if state["logout"]:
                reason = state.get("reason")
                if endpoint.routing["type"] == "http":
                    return cls._single_session_block(endpoint, reason)
                cls._single_session_logout(reason)
                return {"uid": False, "single_session_reason": reason}
        return result

    @classmethod
    def _post_dispatch(cls, response):
        if getattr(request, "_single_session_blocked", False):
            response.set_data(json.dumps({
                "jsonrpc": "2.0", "id": getattr(request.dispatcher, "request_id", None),
                "error": {"code": 100, "message": "Odoo Session Expired", "data": {
                    "name": "odoo.http.SessionExpiredException", "message": "Session expired",
                    "arguments": [], "context": {},
                }},
            }))
            response.headers["Content-Type"] = "application/json"
        return super()._post_dispatch(response)
