import uuid
import logging
from odoo import models, fields, api, SUPERUSER_ID
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    allow_multiple_sessions = fields.Boolean(string="Allow Multiple Sessions", dafault=False)
    session_uuid = fields.Char(string="Session UUID",copy=False)

    @classmethod
    def authenticate(cls, db, credential, user_agent_env):
        auth_info = super().authenticate(db,credential,user_agent_env)
        uid = auth_info.get("uid")
        if uid:
            new_uuid = str(uuid.uuid4())
            with cls.pool.cursor() as cr:
                env = api.Environment(cr,SUPERUSER_ID,{})
                user = env["res.users"].browse(uid)

                # Skip session control for exempted users
                if not user.allow_multiple_sessions:
                    user.write({"session_uuid": new_uuid})
                cr.commit()

            if request and request.session:
                request.session.single_session_uuid = new_uuid

            _logger.info("User %s logged in. UUID=%s",uid,new_uuid)

        return auth_info