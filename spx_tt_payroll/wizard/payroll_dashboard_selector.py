from odoo import fields, models, _
from odoo.exceptions import UserError


class TTPayrollDashboardSelector(models.TransientModel):
    _name = "spx.tt.payroll.dashboard.selector"
    _description = "Select Payroll for Dashboard"

    dashboard_id = fields.Many2one(
        "spx.tt.payroll.dashboard",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        related="dashboard_id.company_id",
        readonly=True,
    )
    payroll_run_id = fields.Many2one(
        "spx.tt.payroll.run",
        string="Payroll Run",
        required=True,
        domain="[('company_id', '=', company_id), ('state', '!=', 'cancelled')]",
    )

    def action_apply(self):
        self.ensure_one()
        if self.payroll_run_id.company_id != self.company_id:
            raise UserError(_("Select a payroll run for the current company."))
        self.dashboard_id.write({"payroll_run_id": self.payroll_run_id.id})
        return self.dashboard_id._dashboard_action()
