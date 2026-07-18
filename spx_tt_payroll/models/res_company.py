from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    tt_payroll_enabled = fields.Boolean(
        string="Enable Trinidad Payroll", default=True
    )
    tt_payroll_default_frequency_id = fields.Many2one(
        "spx.tt.pay.frequency", string="Default Pay Frequency"
    )
    tt_payroll_default_hours_per_day = fields.Float(
        string="Default Hours per Day", default=8.0
    )
    tt_payroll_default_hours_per_week = fields.Float(
        string="Default Hours per Week", default=40.0
    )
    tt_payroll_require_review = fields.Boolean(
        string="Require Payroll Review", default=True
    )
    tt_payroll_require_approval = fields.Boolean(
        string="Require Payroll Approval", default=True
    )
