from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    session_conflict_policy = fields.Selection([
        ("replace_existing", "Allow new login and end the previous session"),
        ("reject_new", "Keep existing session and reject the new login"),
    ], default="replace_existing", required=True,
        config_parameter="single_session_login_pro.conflict_policy")
    session_idle_enabled = fields.Boolean(string="Enable Idle Auto-Logout",
        config_parameter="single_session_login_pro.idle_enabled")
    session_idle_minutes = fields.Integer(string="Idle Timeout", default=30,
        config_parameter="single_session_login_pro.idle_minutes")
    session_warning_minutes = fields.Integer(string="Warning Before Logout", default=2,
        config_parameter="single_session_login_pro.warning_minutes")
    session_retention_days = fields.Integer(string="History Retention", default=30,
        config_parameter="single_session_login_pro.retention_days")

    @api.constrains("session_idle_minutes", "session_warning_minutes", "session_retention_days")
    def _check_session_settings(self):
        for record in self:
            if record.session_idle_minutes <= 0:
                raise ValidationError(_("Idle Timeout must be greater than zero."))
            if not 0 <= record.session_warning_minutes < record.session_idle_minutes:
                raise ValidationError(_("Warning Before Logout must be nonnegative and lower than Idle Timeout."))
            if record.session_retention_days < 0:
                raise ValidationError(_("History Retention must be nonnegative. Use 0 to keep history indefinitely."))
