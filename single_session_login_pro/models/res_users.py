from odoo import fields, models
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    session_policy_revision = fields.Integer(default=0, groups="base.group_system", copy=False)

    def _single_session_prepare_login(self, auth_info, session_uuid):
        # Registration is performed by ir.http only after session.uid is set by
        # Session.finalize(), including trusted-device and MFA completion paths.
        request.session["single_session_pending_uid"] = self.id
        request.session.pop("single_session_pro_registered", None)
        request.session.pop("single_session_reason", None)

    def _single_session_complete_login(self, session_uuid):
        return self.env["user.session"].sudo()._register_session(self, session_uuid)

    def _single_session_validate(self):
        return self.env["user.session"].sudo()._check_current()
