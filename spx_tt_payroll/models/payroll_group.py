from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TTPayrollGroup(models.Model):
    _name = "spx.tt.payroll.group"
    _description = "Trinidad Payroll Group"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "company_id, sequence, name"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    pay_frequency_id = fields.Many2one(
        "spx.tt.pay.frequency",
        required=True,
        default=lambda self: self.env.ref(
            "spx_tt_payroll.pay_frequency_monthly", raise_if_not_found=False
        ),
        tracking=True,
    )
    normal_hours_per_day = fields.Float(default=8.0, tracking=True)
    normal_hours_per_week = fields.Float(default=40.0, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text()
    employee_ids = fields.One2many(
        "hr.employee", "tt_payroll_group_id", string="Employees"
    )
    employee_count = fields.Integer(compute="_compute_employee_count")

    _sql_constraints = [
        (
            "spx_tt_payroll_group_code_company_unique",
            "unique(code, company_id)",
            "The payroll group code must be unique for each company.",
        )
    ]

    @api.depends("employee_ids")
    def _compute_employee_count(self):
        grouped = self.env["hr.employee"]._read_group(
            [("tt_payroll_group_id", "in", self.ids)],
            ["tt_payroll_group_id"],
            ["__count"],
        )
        counts = {group.id: count for group, count in grouped}
        for record in self:
            record.employee_count = counts.get(record.id, 0)

    @api.constrains("normal_hours_per_day", "normal_hours_per_week")
    def _check_hours(self):
        for record in self:
            if record.normal_hours_per_day <= 0:
                raise ValidationError("Normal hours per day must be greater than zero.")
            if record.normal_hours_per_week <= 0:
                raise ValidationError("Normal hours per week must be greater than zero.")

    def action_view_employees(self):
        self.ensure_one()
        action = self.env.ref("spx_tt_payroll.action_tt_payroll_employees").read()[0]
        action["domain"] = [("tt_payroll_group_id", "=", self.id)]
        action["context"] = {
            "default_tt_payroll_enabled": True,
            "default_tt_payroll_group_id": self.id,
            "default_tt_pay_frequency_id": self.pay_frequency_id.id,
        }
        return action
