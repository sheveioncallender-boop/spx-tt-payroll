from odoo import fields, models


class TTPayrollTimeOffSnapshot(models.Model):
    _name = "spx.tt.payroll.time.off.snapshot"
    _description = "Payroll Time Off Snapshot"
    _order = "date_from, leave_type_id, id"
    _check_company_auto = True

    run_employee_id = fields.Many2one(
        "spx.tt.payroll.run.employee", required=True, ondelete="cascade",
        index=True, check_company=True,
    )
    run_id = fields.Many2one(
        "spx.tt.payroll.run", related="run_employee_id.run_id", store=True, index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee", related="run_employee_id.employee_id", store=True, index=True,
    )
    company_id = fields.Many2one(
        "res.company", related="run_employee_id.company_id", store=True, index=True,
    )
    leave_id = fields.Many2one(
        "hr.leave", string="Odoo Time Off", ondelete="set null", index=True, readonly=True,
    )
    leave_type_id = fields.Many2one(
        "hr.leave.type", string="Time Off Type", ondelete="restrict", readonly=True,
    )
    date_from = fields.Datetime(string="Start", readonly=True)
    date_to = fields.Datetime(string="End", readonly=True)
    approval_state = fields.Selection(
        [("approved", "Approved"), ("pending", "Awaiting Approval")],
        required=True, readonly=True, index=True,
    )
    payroll_treatment = fields.Selection(
        [("paid", "Paid Leave"), ("unpaid", "Unpaid Leave"), ("pending", "Not Yet Applied")],
        required=True, readonly=True,
    )
    scheduled_hours = fields.Float(
        string="Scheduled Leave Hours", readonly=True,
        help="Scheduled working hours covered by this Odoo Time Off request within the payroll period.",
    )
    attendance_overlap_hours = fields.Float(
        string="Attendance Overlap", readonly=True,
        help="Hours where an attendance record overlaps this approved Time Off request.",
    )
    payroll_hours = fields.Float(
        string="Hours Applied to Payroll", readonly=True,
        help="Paid leave hours added to payable time. Unpaid or pending Time Off does not add payable hours.",
    )
    note = fields.Char(readonly=True)
