from odoo import http
from odoo.http import request


class SingleSessionCheck(http.Controller):

    @http.route("/single_session/check", type="jsonrpc", auth="user")
    def check(self):
        # Only inspect the authenticated user's protected session fields.
        user = request.env.user.sudo()
        result = user._single_session_validate()
        if result["logout"]:
            request.session.logout(keep_db=True)
        return result
