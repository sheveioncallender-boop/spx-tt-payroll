from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TTPayrollHoursAdjustment(models.Model):
    _name = "spx.tt.payroll.hours.adjustment"
    _description = "Payroll Payable Hours Adjustment"
    _order = "adjusted_at desc, id desc"
    _rec_name = "reason"
    _check_company_auto = True

    run_employee_id = fields.Many2one(
        "spx.tt.payroll.run.employee",
        string="Employee Payroll Calculation",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    run_id = fields.Many2one(
        "spx.tt.payroll.run",
        related="run_employee_id.run_id",
        string="Payroll Run",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="run_employee_id.company_id",
        store=True,
        index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="run_employee_id.employee_id",
        string="Employee",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="run_employee_id.currency_id",
        readonly=True,
    )

    previous_adjustment_hours = fields.Float(string="Previous Adjustment")
    change_hours = fields.Float(
        string="Hours Added / Removed",
        help="Positive hours were added; negative hours were removed.",
    )
    new_adjustment_hours = fields.Float(string="New Adjustment Total")
    previous_payable_hours = fields.Float(string="Previous Payable Hours")
    new_payable_hours = fields.Float(string="New Payable Hours")

    previous_gross_pay = fields.Monetary(
        string="Previous Gross Pay", currency_field="currency_id"
    )
    new_gross_pay = fields.Monetary(
        string="New Gross Pay", currency_field="currency_id"
    )
    previous_net_pay = fields.Monetary(
        string="Previous Net Pay", currency_field="currency_id"
    )
    new_net_pay = fields.Monetary(
        string="New Net Pay", currency_field="currency_id"
    )

    reason = fields.Char(required=True, index=True)
    supporting_note = fields.Text(string="Supporting Note")
    adjusted_by = fields.Many2one(
        "res.users",
        string="Adjusted By",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    adjusted_at = fields.Datetime(
        string="Adjustment Date",
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("tt_payroll_create_hours_audit"):
            raise UserError(
                _("Hours adjustment history can only be created from the Adjust Payable Hours window.")
            )
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("Hours adjustment history is permanent and cannot be edited."))

    def unlink(self):
        raise UserError(_("Hours adjustment history is permanent and cannot be deleted."))
