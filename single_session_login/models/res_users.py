import uuid

from odoo import fields, models
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    allow_multiple_sessions = fields.Boolean(
        string="Allow Multiple Sessions", default=False, groups="base.group_system"
    )
    session_uuid = fields.Char(
        string="Session UUID", copy=False, groups="base.group_system"
    )

    def authenticate(self, credential, user_agent_env):
        auth_info = super().authenticate(credential, user_agent_env)
        uid = auth_info.get("uid")
        # Non-interactive authentication must not evict a browser session.
        if uid and request and user_agent_env and user_agent_env.get("interactive"):
            user = self.sudo().browse(uid)
            new_uuid = str(uuid.uuid4())
            request.session["single_session_uuid"] = new_uuid
            request.session.pop("single_session_pending_uid", None)
            if auth_info.get("mfa") != "skip" and user._mfa_url():
                # Password validation alone is not a completed MFA login.
                request.session["single_session_pending_uid"] = uid
            elif not user.allow_multiple_sessions:
                user.session_uuid = new_uuid
        return auth_info
