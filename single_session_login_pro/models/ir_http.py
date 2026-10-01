from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _single_session_request_state(cls):
        path = request.httprequest.path
        # Reads, bus polling, assets and passive traffic do not extend idle time.
        application_action = path == "/web/dataset/call_button" or (
            (path == "/web/dataset/call_kw" or path.startswith("/web/dataset/call_kw/"))
            and request.params.get("method") in {"create", "write", "unlink", "web_save"}
        )
        return request.env["user.session"].sudo()._check_current(touch=application_action)

    @classmethod
    def _single_session_record_logout(cls):
        request.env["user.session"].sudo()._current()._end("user_logout")

    @classmethod
    def _single_session_complete_pending(cls):
        return request.env["user.session"].sudo()._check_current()
