from odoo import models, fields

class UserSession(models.Model):
    _name = "user.session"
    _description = "User Session"

    user_id = fields.Many2one("res.users",required=True,ondelete="cascade")
    session_id = fields.Char(required=True)
    login_time = fields.Datetime(default=fields.Datetime.now)
    active = fields.Boolean(default=True)