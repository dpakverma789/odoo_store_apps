from odoo import http
from odoo.http import request


class SingleSessionCheck(http.Controller):

    @http.route("/single_session/check",type="json",auth="user")
    def check(self):
        user = request.env.user
        if user.allow_multiple_sessions:
            return {
                "logout": False
            }
        db_uuid = user.session_uuid
        session_uuid = getattr(request.session, "single_session_uuid", False)
        if not session_uuid:
            request.session.logout()
            return {
                "logout": True
            }

        if db_uuid != session_uuid:
            request.session.logout()
            return {
                "logout": True
            }

        return {
            "logout": False
        }