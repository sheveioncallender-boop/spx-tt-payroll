from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class TTPayrollAttentionWizard(models.TransientModel):
    _name = "spx.tt.payroll.attention.wizard"
    _description = "Payroll Items Needing Attention"

    run_employee_id = fields.Many2one(
        "spx.tt.payroll.run.employee",
        string="Employee Payroll Calculation",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="run_employee_id.employee_id",
        string="Employee",
        readonly=True,
    )
    payroll_run_id = fields.Many2one(
        "spx.tt.payroll.run",
        related="run_employee_id.run_id",
        string="Payroll Run",
        readonly=True,
    )
    issue_count = fields.Integer(
        string="Items Needing Attention",
        compute="_compute_issue_count",
    )
    issue_line_ids = fields.One2many(
        "spx.tt.payroll.attention.wizard.line",
        "wizard_id",
        string="Items Needing Attention",
        readonly=True,
    )

    @api.depends("issue_line_ids")
    def _compute_issue_count(self):
        for wizard in self:
            wizard.issue_count = len(wizard.issue_line_ids)

    @api.model
    def create_for_calculation(self, calculation):
        calculation.ensure_one()
        wizard = self.create({"run_employee_id": calculation.id})
        items = calculation._get_attention_items()
        if items:
            self.env["spx.tt.payroll.attention.wizard.line"].create(
                [
                    {
                        "wizard_id": wizard.id,
                        "run_employee_id": calculation.id,
                        "sequence": item.get("sequence", 10),
                        "issue_code": item["code"],
                        "title": item["title"],
                        "detail": item.get("detail") or False,
                        "action_kind": item.get("action_kind") or "calculation",
                        "action_label": item.get("action_label") or _("Review"),
                    }
                    for item in items
                ]
            )
        return wizard


class TTPayrollAttentionWizardLine(models.TransientModel):
    _name = "spx.tt.payroll.attention.wizard.line"
    _description = "Payroll Attention Item"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "spx.tt.payroll.attention.wizard",
        required=True,
        ondelete="cascade",
    )
    run_employee_id = fields.Many2one(
        "spx.tt.payroll.run.employee",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    issue_code = fields.Char(required=True, readonly=True)
    title = fields.Char(string="Item", required=True, readonly=True)
    detail = fields.Text(string="What to do", readonly=True)
    action_kind = fields.Selection(
        [
            ("employee_profile", "Employee Profile"),
            ("statutory_profile", "Statutory Profile"),
            ("attendances", "Attendances"),
            ("refresh_attendance", "Refresh Attendance"),
            ("adjust_hours", "Adjust Payable Hours"),
            ("confirm_attendance", "Confirm Attendance"),
            ("recalculate", "Recalculate Pay"),
            ("calculation", "Payroll Calculation"),
        ],
        required=True,
        readonly=True,
    )
    action_label = fields.Char(string="Action", required=True, readonly=True)

    def _require_payroll_officer(self):
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_officer"):
            raise AccessError(
                _("Payroll Officer access is required to resolve payroll attention items.")
            )

    def action_resolve(self):
        self.ensure_one()
        calculation = self.run_employee_id.exists()
        if not calculation:
            raise UserError(_("The employee payroll calculation no longer exists."))

        if self.action_kind == "employee_profile":
            return calculation.action_open_employee_profile()
        if self.action_kind == "statutory_profile":
            return calculation.employee_id.action_tt_open_statutory_profile()
        if self.action_kind == "attendances":
            return calculation.action_open_attendances()

        self._require_payroll_officer()
        if self.action_kind == "refresh_attendance":
            calculation.action_refresh_attendance()
            return calculation.action_open_calculation()
        if self.action_kind == "adjust_hours":
            return calculation.action_open_hours_adjustment_wizard()
        if self.action_kind == "confirm_attendance":
            calculation.action_confirm_attendance()
            return calculation.action_open_calculation()
        if self.action_kind == "recalculate":
            calculation.action_recalculate_earnings()
            return calculation.action_open_calculation()
        return calculation.action_open_calculation()
