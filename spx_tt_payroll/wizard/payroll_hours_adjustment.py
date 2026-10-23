from ..models.calculation_security import INTERNAL
from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero


class TTPayrollHoursAdjustmentWizard(models.TransientModel):
    _name = "spx.tt.payroll.hours.adjustment.wizard"
    _description = "Adjust Payroll Payable Hours"

    run_employee_id = fields.Many2one(
        "spx.tt.payroll.run.employee",
        string="Employee Payroll Calculation",
        required=True,
        readonly=True,
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
    current_adjustment_hours = fields.Float(
        string="Current Adjustment",
        related="run_employee_id.attendance_adjustment_hours",
        readonly=True,
    )
    current_payable_hours = fields.Float(
        string="Current Payable Hours",
        related="run_employee_id.payable_hours",
        readonly=True,
    )
    expected_hours = fields.Float(
        string="Expected Hours",
        related="run_employee_id.scheduled_hours",
        readonly=True,
    )
    adjustment_hours = fields.Float(
        string="Hours to Add or Remove",
        required=True,
        help="Enter a positive number to add hours or a negative number to remove hours.",
    )
    new_adjustment_total = fields.Float(
        string="New Adjustment Total",
        compute="_compute_preview",
        readonly=True,
    )
    estimated_payable_hours = fields.Float(
        string="Estimated Payable Hours",
        compute="_compute_preview",
        readonly=True,
    )
    reason = fields.Char(
        string="Reason",
        required=True,
        help="Explain why the payable hours are being changed.",
    )
    supporting_note = fields.Text(
        string="Supporting Note",
        help="Optional additional details, approval reference, or department confirmation.",
    )

    @api.depends(
        "adjustment_hours",
        "run_employee_id.attendance_adjustment_hours",
        "run_employee_id.regular_hours",
        "run_employee_id.paid_leave_hours",
        "run_employee_id.public_holiday_hours",
        "run_employee_id.scheduled_hours",
        "run_employee_id.pay_basis",
    )
    def _compute_preview(self):
        for wizard in self:
            line = wizard.run_employee_id
            new_total = (line.attendance_adjustment_hours or 0.0) + (
                wizard.adjustment_hours or 0.0
            )
            payable = max(
                0.0,
                (line.regular_hours or 0.0)
                + (line.paid_leave_hours or 0.0)
                + (line.public_holiday_hours or 0.0)
                + new_total,
            )
            if line.pay_basis == "salary" and line.scheduled_hours > 0:
                payable = min(line.scheduled_hours, payable)
            wizard.new_adjustment_total = new_total
            wizard.estimated_payable_hours = payable

    @api.constrains("reason")
    def _check_reason(self):
        for wizard in self:
            if not (wizard.reason or "").strip():
                raise ValidationError(_("Enter a reason for the hours adjustment."))

    def action_apply_adjustment(self):
        self.ensure_one()
        line = self.run_employee_id.exists()
        if not line:
            raise UserError(_("The employee payroll calculation no longer exists."))
        line._check_editable()
        if float_is_zero(self.adjustment_hours, precision_digits=4):
            raise UserError(_("Enter the number of hours to add or remove."))
        reason = (self.reason or "").strip()
        if not reason:
            raise UserError(_("Enter a reason for the hours adjustment."))

        previous_adjustment = line.attendance_adjustment_hours
        previous_payable = line.payable_hours
        previous_gross = line.gross_pay
        previous_net = line.net_pay
        new_adjustment = previous_adjustment + self.adjustment_hours

        line.with_context(tt_payroll_hours_wizard=INTERNAL).write(
            {"attendance_adjustment_hours": new_adjustment}
        )
        # Stored computed totals are normally refreshed by the rebuilt item lines.
        # Reading them after the write gives the exact values saved by payroll.
        line.invalidate_recordset(
            ["payable_hours", "gross_pay", "total_deductions", "net_pay"]
        )

        audit = self.env["spx.tt.payroll.hours.adjustment"].sudo().with_context(
            tt_payroll_create_hours_audit=INTERNAL
        ).create(
            {
                "run_employee_id": line.id,
                "previous_adjustment_hours": previous_adjustment,
                "change_hours": self.adjustment_hours,
                "new_adjustment_hours": line.attendance_adjustment_hours,
                "previous_payable_hours": previous_payable,
                "new_payable_hours": line.payable_hours,
                "previous_gross_pay": previous_gross,
                "new_gross_pay": line.gross_pay,
                "previous_net_pay": previous_net,
                "new_net_pay": line.net_pay,
                "reason": reason,
                "supporting_note": self.supporting_note,
                "adjusted_by": self.env.user.id,
                "adjusted_at": fields.Datetime.now(),
            }
        )

        def _money(value):
            amount = f"{value:,.2f}"
            symbol = line.currency_id.symbol or ""
            if not symbol:
                return amount
            if line.currency_id.position == "after":
                return f"{amount} {symbol}"
            return f"{symbol}{amount}"

        note = Markup(
            "<p><strong>Payable hours adjusted</strong></p>"
            "<ul>"
            "<li>Hours added/removed: %(change)s</li>"
            "<li>Adjustment total: %(old_adjustment)s → %(new_adjustment)s</li>"
            "<li>Payable hours: %(old_payable)s → %(new_payable)s</li>"
            "<li>Gross pay: %(old_gross)s → %(new_gross)s</li>"
            "<li>Net pay: %(old_net)s → %(new_net)s</li>"
            "<li>Reason: %(reason)s</li>"
            "</ul>"
        ) % {
            "change": escape("%.2f" % self.adjustment_hours),
            "old_adjustment": escape("%.2f" % previous_adjustment),
            "new_adjustment": escape("%.2f" % line.attendance_adjustment_hours),
            "old_payable": escape("%.2f" % previous_payable),
            "new_payable": escape("%.2f" % line.payable_hours),
            "old_gross": escape(_money(previous_gross)),
            "new_gross": escape(_money(line.gross_pay)),
            "old_net": escape(_money(previous_net)),
            "new_net": escape(_money(line.net_pay)),
            "reason": escape(reason),
        }
        if self.supporting_note:
            note += Markup("<p><strong>Supporting note:</strong> %(note)s</p>") % {
                "note": escape(self.supporting_note)
            }
        line.message_post(body=note)

        return {"type": "ir.actions.client", "tag": "reload"}
