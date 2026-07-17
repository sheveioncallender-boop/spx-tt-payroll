from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tt_payroll_enabled = fields.Boolean(
        related="company_id.tt_payroll_enabled", readonly=False
    )
    tt_payroll_default_frequency_id = fields.Many2one(
        related="company_id.tt_payroll_default_frequency_id", readonly=False
    )
    tt_payroll_default_hours_per_day = fields.Float(
        related="company_id.tt_payroll_default_hours_per_day", readonly=False
    )
    tt_payroll_default_hours_per_week = fields.Float(
        related="company_id.tt_payroll_default_hours_per_week", readonly=False
    )
    tt_payroll_require_review = fields.Boolean(
        related="company_id.tt_payroll_require_review", readonly=False
    )
    tt_payroll_require_approval = fields.Boolean(
        related="company_id.tt_payroll_require_approval", readonly=False
    )
