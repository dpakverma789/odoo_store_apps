# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request
from odoo.tools.misc import str2bool
from odoo.addons.web.models.ir_http import ALLOWED_DEBUG_MODES  # ['', '1', 'assets', 'tests']

class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _handle_debug(cls):
        """
        Gate enabling debug modes behind a group, without assuming a logged user
        is already available on request.env.user (which can be empty here).
        """
        debug_param = request.httprequest.args.get("debug")
        if debug_param is not None:
            requested = [m.strip() for m in (debug_param or "").split(",")]
            wants_enable = any(
                (m in ALLOWED_DEBUG_MODES and m != "") or str2bool(m, m)
                for m in requested
            )
            if wants_enable:
                uid = request.session.uid
                allowed = False
                if uid:
                    user = request.env["res.users"].sudo().browse(uid)
                    if user and user.exists():
                        allowed = user.has_group("debug_mode_security.group_enable_debug")
                if not allowed:
                    request.session.debug = ""
                    return

        return super()._handle_debug()
