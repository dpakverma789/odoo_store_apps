import hashlib
import math
import uuid
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from odoo.http import request


REASONS = [
    ("user_logout", "User Logout"),
    ("replaced_by_new_login", "Replaced by New Login"),
    ("new_login_rejected", "New Login Rejected"),
    ("idle_timeout", "Idle Timeout"),
    ("admin_revoked", "Administrator Revoked"),
    ("session_invalidated", "Session Invalidated"),
]


class UserSession(models.Model):
    _name = "user.session"
    _description = "User Session"
    _order = "login_datetime desc, id desc"
    _rec_name = "user_id"

    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")
    session_reference = fields.Char(required=True, index=True, copy=False)
    login_datetime = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    last_activity_datetime = fields.Datetime(required=True, default=fields.Datetime.now)
    end_datetime = fields.Datetime(index=True)
    active = fields.Boolean(default=True, index=True)
    status = fields.Selection([
        ("active", "Active"), ("ended", "Ended"),
        ("expired", "Expired"), ("rejected", "Rejected"),
    ], required=True, default="active", index=True)
    end_reason = fields.Selection(REASONS)
    ip_address = fields.Char()
    user_agent = fields.Char()
    browser = fields.Char()
    revoked_by = fields.Many2one("res.users", ondelete="set null")
    duration_minutes = fields.Float(compute="_compute_duration", string="Duration (minutes)")

    _reference_unique = models.Constraint("UNIQUE(session_reference)", "Session reference must be unique.")

    @api.depends("login_datetime", "end_datetime")
    def _compute_duration(self):
        now = fields.Datetime.now()
        for record in self:
            record.duration_minutes = max(0, ((record.end_datetime or now) - record.login_datetime).total_seconds() / 60)

    @api.model
    def _settings(self):
        params = self.env["ir.config_parameter"].sudo()
        def number(key, default):
            try:
                return int(params.get_param("single_session_login_pro." + key, default))
            except (ValueError, TypeError):
                return default
        timeout = max(1, number("idle_minutes", 30))
        return {
            "enabled": params.get_param("single_session_login_pro.idle_enabled", "False") == "True",
            "timeout": timeout * 60,
            "warning": max(0, min(number("warning_minutes", 2), timeout - 1)) * 60,
            "policy": params.get_param("single_session_login_pro.conflict_policy", "replace_existing"),
            "retention": max(0, number("retention_days", 30)),
        }

    @api.model
    def _reference(self, token):
        return hashlib.sha256(token.encode()).hexdigest()

    def _end(self, reason, administrator=None):
        # UPDATE locks the row; a competing transaction is retried by Odoo.
        # The status predicate makes repeat calls idempotent.
        if not self:
            return
        self.flush_recordset()
        status = "expired" if reason == "idle_timeout" else "rejected" if reason == "new_login_rejected" else "ended"
        self.env.cr.execute("""
            UPDATE user_session SET active = false, status = %s, end_reason = %s,
                end_datetime = %s, revoked_by = %s
            WHERE id IN %s AND status = 'active'
            RETURNING id
        """, [status, reason, fields.Datetime.now(), administrator or None, tuple(self.ids)])
        changed = self.browse([row[0] for row in self.env.cr.fetchall()])
        changed.invalidate_recordset()
        changed.modified(["active", "status", "end_reason", "end_datetime", "revoked_by"])

    def _expire(self, settings=None):
        settings = settings or self._settings()
        if settings["enabled"]:
            cutoff = fields.Datetime.now() - timedelta(seconds=settings["timeout"])
            self.filtered(lambda row: row.status == "active" and row.last_activity_datetime <= cutoff)._end("idle_timeout")

    @api.model
    def _register_session(self, user, token):
        # A write, not just an advisory lock: under PostgreSQL REPEATABLE READ
        # competing logins must restart with a fresh snapshot after waiting.
        self.env.cr.execute("""UPDATE res_users
            SET session_policy_revision = COALESCE(session_policy_revision, 0) + 1
            WHERE id = %s RETURNING id""", [user.id])
        user.invalidate_recordset(["session_policy_revision", "allow_multiple_sessions"])
        reference = self._reference(token)
        existing = self.with_context(active_test=False).search([("session_reference", "=", reference)], limit=1)
        if existing:
            return existing
        active = self.search([("user_id", "=", user.id), ("status", "=", "active")])
        settings = self._settings()
        active._expire(settings)
        active = active.filtered(lambda row: row.status == "active")
        rejected = bool(active and not user.allow_multiple_sessions and settings["policy"] == "reject_new")
        if active and not user.allow_multiple_sessions and not rejected:
            active._end("replaced_by_new_login")
        agent = request.httprequest.user_agent if request else None
        record = self.create({
            "user_id": user.id, "session_reference": reference,
            "ip_address": request.httprequest.remote_addr if request else False,
            "user_agent": str(agent)[:512] if agent else False,
            "browser": self._browser_label(str(agent)) if agent else False,
        })
        if rejected:
            record._end("new_login_rejected")
        elif not user.allow_multiple_sessions:
            user.session_uuid = token
        return record

    @api.model
    def _browser_label(self, agent):
        browser = next((name for marker, name in [("Edg/", "Edge"), ("OPR/", "Opera"),
            ("Firefox/", "Firefox"), ("Chrome/", "Chrome"), ("Safari/", "Safari")] if marker in agent), "Other")
        platform = next((name for marker, name in [("Android", "Android"), ("iPhone", "iOS"),
            ("iPad", "iOS"), ("Windows", "Windows"), ("Macintosh", "macOS"), ("Linux", "Linux")] if marker in agent), "Other")
        return f"{browser} / {platform}"

    @api.model
    def _current(self):
        token = request.session.get("single_session_uuid")
        if not token or not request.session.uid:
            return self.browse()
        return self.with_context(active_test=False).search([
            ("session_reference", "=", self._reference(token)),
            ("user_id", "=", request.session.uid),
        ], limit=1)

    @api.model
    def _activate_current(self):
        if not request.session.uid:
            return
        if request.session.get("single_session_pro_registered"):
            return
        user = self.env["res.users"].sudo().browse(request.session.uid)
        token = request.session.get("single_session_uuid")
        pending = request.session.get("single_session_pending_uid")
        # Existing free sessions can migrate only if still valid. Sessions from
        # before installation without a marker must sign in again.
        if pending != user.id and (not token or (not user.allow_multiple_sessions and user.session_uuid != token)):
            return
        record = user._single_session_complete_login(token or str(uuid.uuid4()))
        request.session.pop("single_session_pending_uid", None)
        request.session["single_session_pro_registered"] = True
        return record

    @api.model
    def _check_current(self, touch=False):
        self._activate_current()
        record = self._current()
        if not record:
            return {"logout": True, "reason": "session_invalidated"}
        settings = self._settings()
        record._expire(settings)
        if record.status != "active":
            return {"logout": True, "reason": record.end_reason or "session_invalidated"}
        now = fields.Datetime.now()
        if touch:
            record.last_activity_datetime = now
        result = {"logout": False}
        if settings["enabled"]:
            remaining = max(0, math.ceil(settings["timeout"] - (now - record.last_activity_datetime).total_seconds()))
            result.update(seconds_remaining=remaining,
                          warning=bool(settings["warning"] and remaining <= settings["warning"]),
                          warning_reason="idle_timeout")
        return result

    def action_end_session(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only system administrators can end sessions."))
        self.check_access("read")
        self.sudo()._end("admin_revoked", self.env.uid)
        return True

    @api.model
    def _cron_expire(self):
        settings = self._settings()
        if settings["enabled"]:
            cutoff = fields.Datetime.now() - timedelta(seconds=settings["timeout"])
            self.search([("status", "=", "active"), ("last_activity_datetime", "<=", cutoff)])._end("idle_timeout")

    @api.model
    def _cron_cleanup(self):
        days = self._settings()["retention"]
        if days:
            self.with_context(active_test=False).search([
                ("status", "in", ["ended", "expired", "rejected"]),
                ("end_datetime", "<", fields.Datetime.now() - timedelta(days=days)),
            ]).unlink()
