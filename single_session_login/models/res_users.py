import uuid

from odoo import fields, models
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    allow_multiple_sessions = fields.Boolean(
        string="Allow Multiple Sessions", default=False, groups="base.group_system",
        help="When enabled, this user is exempt from single-session restrictions.",
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
            user._single_session_prepare_login(auth_info, new_uuid)
        return auth_info

    def _single_session_prepare_login(self, auth_info, session_uuid):
        self.ensure_one()
        if auth_info.get("mfa") != "skip" and self._mfa_url():
            # Password validation alone is not a completed MFA login.
            request.session["single_session_pending_uid"] = self.id
        else:
            self._single_session_complete_login(session_uuid)

    def _single_session_complete_login(self, session_uuid):
        self.ensure_one()
        if not self.allow_multiple_sessions:
            self.session_uuid = session_uuid

    def _single_session_validate(self):
        self.ensure_one()
        session_uuid = request.session.get("single_session_uuid")
        pending_uid = request.session.pop("single_session_pending_uid", None)
        if pending_uid == self.id and session_uuid:
            self._single_session_complete_login(session_uuid)
        if self.allow_multiple_sessions:
            return {"logout": False}
        return {"logout": not session_uuid or self.session_uuid != session_uuid}
