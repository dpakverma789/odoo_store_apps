from odoo import http
from odoo.http import request


class SingleSessionCheck(http.Controller):

    @http.route("/single_session/check", type="jsonrpc", auth="user")
    def check(self):
        # Only inspect the authenticated user's protected session fields.
        user = request.env.user.sudo()
        session_uuid = request.session.get("single_session_uuid")
        pending_uid = request.session.pop("single_session_pending_uid", None)
        if pending_uid == user.id and session_uuid and not user.allow_multiple_sessions:
            # auth='user' ensures the second authentication factor has succeeded.
            user.session_uuid = session_uuid

        if user.allow_multiple_sessions:
            return {"logout": False}
        if not session_uuid or user.session_uuid != session_uuid:
            request.session.logout(keep_db=True)
            return {"logout": True}
        return {"logout": False}
