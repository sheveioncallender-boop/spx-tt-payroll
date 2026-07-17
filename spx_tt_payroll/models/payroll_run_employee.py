from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TTPayrollRunEmployee(models.Model):
    _name = "spx.tt.payroll.run.employee"
    _description = "Employee Payroll Calculation"
    _rec_name = "employee_id"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "run_id, department_id, employee_id"
    _check_company_auto = True

    run_id = fields.Many2one(
        "spx.tt.payroll.run",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    run_state = fields.Selection(related="run_id.state", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        related="run_id.company_id",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="run_id.currency_id",
        readonly=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
        tracking=True,
        domain="[('active', '=', True), ('company_id', '=', company_id), ('tt_payroll_status', '!=', 'excluded')]",
    )
    employee_image = fields.Binary(related="employee_id.image_128", readonly=True)
    employee_number = fields.Char(string="Employee / Clock ID", copy=False)
    job_title = fields.Char(string="Job Title")
    department_id = fields.Many2one("hr.department", string="Department")
    pay_frequency_id = fields.Many2one("spx.tt.pay.frequency", string="Pay Frequency")
    payroll_group_id = fields.Many2one("spx.tt.payroll.group", string="Payroll Group")

    # pay_type and base_rate are retained for compatibility with Phase 2A records.
    pay_type = fields.Selection(
        [
            ("monthly", "Monthly Salary"),
            ("weekly", "Weekly Salary"),
            ("daily", "Daily Paid"),
            ("hourly", "Hourly Paid"),
        ],
        string="Legacy Pay Type",
    )
    pay_basis = fields.Selection(
        [("salary", "Salaried"), ("hourly", "Hourly Paid")],
        string="Pay Basis",
        index=True,
    )
    salary_amount = fields.Monetary(
        string="Monthly Salary",
        currency_field="currency_id",
        help="The employee's monthly salary copied from the TT Payroll employee profile.",
    )
    hourly_rate = fields.Monetary(
        string="Hourly Rate",
        currency_field="currency_id",
    )
    period_salary = fields.Monetary(
        string="Salary for this Pay Period",
        currency_field="currency_id",
        help="The monthly salary converted to the payroll run's frequency before attendance proration.",
    )
    effective_hourly_rate = fields.Monetary(
        string="Payroll Hourly Equivalent",
        currency_field="currency_id",
        help="Used to show how Salary or Regular Hours was calculated for this payroll period.",
    )
    base_rate = fields.Monetary(string="Base Rate (Legacy)", currency_field="currency_id")
    pay_unit = fields.Char(string="Pay Unit")
    normal_hours_per_day = fields.Float(string="Normal Hours per Day")
    normal_hours_per_week = fields.Float(string="Normal Hours per Week")
    payment_method = fields.Selection(
        [("bank", "Bank Transfer"), ("cash", "Cash"), ("cheque", "Cheque")],
        string="Payment Method",
    )
    bank_name = fields.Char(string="Bank")
    bank_account_number = fields.Char(string="Account Number")
    bir_number = fields.Char(string="BIR Number")
    nis_number = fields.Char(string="NIS Number")
    nis_exempt = fields.Boolean(string="NIS Exempt")
    health_surcharge_exempt = fields.Boolean(string="Health Surcharge Exempt")

    # Attendance snapshot. These values are copied into the payroll run so later
    # changes to Odoo Attendances do not silently change a reviewed payroll.
    scheduled_days = fields.Float(string="Scheduled Days")
    scheduled_hours = fields.Float(string="Expected Hours")
    attendance_record_count = fields.Integer(string="Attendance Records")
    incomplete_attendance_count = fields.Integer(string="Missing Check-outs")
    actual_worked_hours = fields.Float(string="Clocked Hours")
    regular_hours = fields.Float(string="Regular Worked Hours")
    overtime_hours = fields.Float(string="Approved Overtime Hours")
    pending_overtime_hours = fields.Float(string="Overtime Awaiting Approval")
    public_holiday_hours = fields.Float(string="Public Holiday Hours")
    paid_leave_hours = fields.Float(string="Approved Paid Leave Hours")
    unpaid_leave_hours = fields.Float(string="Approved Unpaid Leave Hours")
    attendance_adjustment_hours = fields.Float(
        string="Manual Payable Hours Adjustment",
        help="Use a positive or negative adjustment after reviewing a clocking, leave, or other payroll issue.",
    )
    payable_hours = fields.Float(
        string="Final Payable Hours",
        help="Regular worked hours plus payable leave/public-holiday hours and approved manual adjustments. Overtime is paid separately.",
    )
    unpaid_hours = fields.Float(string="Unpaid / Missing Hours")
    attendance_loaded_at = fields.Datetime(string="Attendance Pulled At", readonly=True)
    attendance_confirmed = fields.Boolean(string="Attendance Confirmed", copy=False)
    attendance_review_note = fields.Text(
        string="Attendance Review Note",
        help="Explain clocking corrections, paid leave decisions, or accepted unpaid hours.",
    )
    attendance_issue_summary = fields.Text(string="Attendance Issues", readonly=True)
    attendance_status = fields.Selection(
        [
            ("not_loaded", "Not Loaded"),
            ("needs_attention", "Needs Attention"),
            ("ready", "Ready"),
        ],
        default="not_loaded",
        string="Attendance Status",
        tracking=True,
    )

    item_line_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Payroll Items",
        copy=True,
    )
    earning_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Earnings",
        domain=[("category", "=", "earning")],
    )
    deduction_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Deductions",
        domain=[("category", "=", "deduction")],
    )
    employer_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Employer Contributions",
        domain=[("category", "=", "employer")],
    )

    gross_pay = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    taxable_earnings = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    nis_insurable_earnings = fields.Monetary(
        string="NIS Insurable Earnings",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    total_deductions = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    employer_contribution_total = fields.Monetary(
        string="Employer Contributions",
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )
    net_pay = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_totals",
        store=True,
    )

    review_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("reviewed", "Reviewed"),
            ("on_hold", "On Hold"),
            ("excluded", "Excluded"),
        ],
        default="pending",
        required=True,
        copy=False,
        tracking=True,
    )
    display_status = fields.Selection(
        [
            ("ready", "Ready"),
            ("needs_attention", "Needs Attention"),
            ("reviewed", "Reviewed"),
            ("on_hold", "On Hold"),
            ("excluded", "Excluded"),
        ],
        string="Status",
        compute="_compute_issues_and_status",
        store=True,
    )
    issue_count = fields.Integer(
        string="Items Requiring Attention",
        compute="_compute_issues_and_status",
        store=True,
    )
    issue_summary = fields.Text(
        string="Items Requiring Attention",
        compute="_compute_issues_and_status",
        store=True,
    )
    hold_reason = fields.Char(string="Hold / Exclusion Reason")
    notes = fields.Text()

    _sql_constraints = [
        (
            "spx_tt_run_employee_unique",
            "unique(run_id, employee_id)",
            "An employee can only appear once in the same payroll run.",
        )
    ]

    @api.model
    def _period_salary_from_monthly(self, monthly_salary, run):
        code = run.pay_frequency_id.code if run.pay_frequency_id else ""
        multipliers = {
            "MONTHLY": 1.0,
            "SEMI_MONTHLY": 0.5,
            "FORTNIGHTLY": 12.0 / 26.0,
            "WEEKLY": 12.0 / 52.0,
            "OFF_CYCLE": 0.0,
        }
        return monthly_salary * multipliers.get(code, 1.0)

    @api.model
    def _employee_snapshot_values(self, employee, run):
        pay_basis = employee.tt_pay_basis
        salary_amount = employee.tt_monthly_salary if pay_basis == "salary" else 0.0
        hourly_rate = employee.tt_hourly_rate if pay_basis == "hourly" else 0.0
        base_rate = salary_amount if pay_basis == "salary" else hourly_rate
        pay_unit = "Month" if pay_basis == "salary" else "Hour"
        primary_bank = employee.primary_bank_account_id
        bank_name = employee.tt_bank_name or (
            primary_bank.bank_id.name if primary_bank and primary_bank.bank_id else ""
        )
        bank_account_number = employee.tt_bank_account_number or (
            primary_bank.acc_number if primary_bank else ""
        )
        return {
            "employee_number": employee.barcode or "",
            "job_title": employee.job_title or employee.job_id.name or "",
            "department_id": employee.department_id.id,
            "pay_frequency_id": employee.tt_pay_frequency_id.id,
            "payroll_group_id": employee.tt_payroll_group_id.id,
            "pay_type": employee.tt_pay_type,
            "pay_basis": pay_basis,
            "salary_amount": salary_amount,
            "hourly_rate": hourly_rate,
            "period_salary": self._period_salary_from_monthly(salary_amount, run),
            "base_rate": base_rate,
            "pay_unit": pay_unit,
            "normal_hours_per_day": employee.tt_normal_hours_per_day,
            "normal_hours_per_week": employee.tt_normal_hours_per_week,
            "payment_method": employee.tt_payment_method,
            "bank_name": bank_name,
            "bank_account_number": bank_account_number,
            "bir_number": employee.tt_bir_number,
            "nis_number": employee.tt_nis_number,
            "nis_exempt": employee.tt_nis_exempt,
            "health_surcharge_exempt": employee.tt_health_surcharge_exempt,
            "review_state": "on_hold" if employee.tt_payroll_status == "on_hold" else "pending",
        }

    @api.onchange("employee_id", "run_id")
    def _onchange_employee_id(self):
        if self.employee_id and self.run_id:
            self.update(self._employee_snapshot_values(self.employee_id, self.run_id))

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            employee_id = vals.get("employee_id")
            run_id = vals.get("run_id")
            employee = (
                self.env["hr.employee"].browse(employee_id).exists()
                if employee_id
                else self.env["hr.employee"]
            )
            run = (
                self.env["spx.tt.payroll.run"].browse(run_id).exists()
                if run_id
                else self.env["spx.tt.payroll.run"]
            )
            if employee and run:
                snapshot = self._employee_snapshot_values(employee, run)
                for key, value in snapshot.items():
                    vals.setdefault(key, value)
            prepared_vals_list.append(vals)

        records = super().create(prepared_vals_list)
        records._pull_attendance_snapshot()
        records._load_default_items()
        return records

    @api.depends(
        "item_line_ids.amount",
        "item_line_ids.category",
        "item_line_ids.taxable",
        "item_line_ids.nis_applicable",
    )
    def _compute_totals(self):
        for line in self:
            earnings = line.item_line_ids.filtered(lambda item: item.category == "earning")
            deductions = line.item_line_ids.filtered(lambda item: item.category == "deduction")
            employer_items = line.item_line_ids.filtered(lambda item: item.category == "employer")
            line.gross_pay = sum(earnings.mapped("amount"))
            line.taxable_earnings = sum(earnings.filtered("taxable").mapped("amount"))
            line.nis_insurable_earnings = sum(
                earnings.filtered("nis_applicable").mapped("amount")
            )
            line.total_deductions = sum(deductions.mapped("amount"))
            line.employer_contribution_total = sum(employer_items.mapped("amount"))
            line.net_pay = line.gross_pay - line.total_deductions

    @api.depends(
        "pay_basis",
        "pay_frequency_id",
        "salary_amount",
        "hourly_rate",
        "payment_method",
        "bank_name",
        "bank_account_number",
        "bir_number",
        "nis_number",
        "nis_exempt",
        "attendance_status",
        "attendance_confirmed",
        "gross_pay",
        "net_pay",
        "item_line_ids.amount",
        "item_line_ids.quantity",
        "item_line_ids.source",
        "item_line_ids.category",
        "item_line_ids.statutory_code",
        "review_state",
    )
    def _compute_issues_and_status(self):
        required_statutory = {"paye", "employee_nis", "health_surcharge", "employer_nis"}
        for line in self:
            issues = []
            if not line.pay_basis:
                issues.append(_("Pay basis is missing."))
            if not line.pay_frequency_id:
                issues.append(_("Pay frequency is missing."))
            if line.pay_basis == "salary" and line.salary_amount <= 0:
                issues.append(_("Salary is missing."))
            if line.pay_basis == "hourly" and line.hourly_rate <= 0:
                issues.append(_("Hourly rate is missing."))
            if not line.bir_number:
                issues.append(_("BIR number is missing."))
            if not line.nis_exempt and not line.nis_number:
                issues.append(_("NIS number is missing."))
            if line.payment_method == "bank":
                if not line.bank_name:
                    issues.append(_("Bank name is missing."))
                if not line.bank_account_number:
                    issues.append(_("Bank account number is missing."))
            if line.attendance_status == "not_loaded":
                issues.append(_("Attendance has not been pulled."))
            elif line.attendance_status == "needs_attention" and not line.attendance_confirmed:
                issues.append(_("Attendance needs review."))
            if not line.item_line_ids.filtered(lambda item: item.category == "earning"):
                issues.append(_("No earnings have been generated."))
            current_statutory = set(
                line.item_line_ids.filtered(
                    lambda item: item.statutory_code != "none"
                ).mapped("statutory_code")
            )
            if required_statutory - current_statutory:
                issues.append(_("One or more standard statutory lines are missing."))
            if line.net_pay < 0:
                issues.append(_("Net pay is negative."))

            line.issue_count = len(issues)
            line.issue_summary = "\n".join("• %s" % issue for issue in issues)
            if line.review_state == "excluded":
                line.display_status = "excluded"
            elif line.review_state == "on_hold":
                line.display_status = "on_hold"
            elif issues:
                line.display_status = "needs_attention"
            elif line.review_state == "reviewed":
                line.display_status = "reviewed"
            else:
                line.display_status = "ready"

    def _period_bounds(self):
        self.ensure_one()
        employee_tz = self.employee_id._get_tz() or "UTC"
        tz = pytz.timezone(employee_tz)
        start_local = tz.localize(datetime.combine(self.run_id.date_start, time.min))
        end_local = tz.localize(
            datetime.combine(self.run_id.date_end + timedelta(days=1), time.min)
        )
        start_utc_aware = start_local.astimezone(pytz.UTC)
        end_utc_aware = end_local.astimezone(pytz.UTC)
        return (
            tz,
            start_utc_aware,
            end_utc_aware,
            start_utc_aware.replace(tzinfo=None),
            end_utc_aware.replace(tzinfo=None),
        )

    def _scheduled_hours_and_days(self, start_aware, end_aware, tz):
        self.ensure_one()
        employee = self.employee_id
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if not calendar or not employee.resource_id:
            return 0.0, 0.0
        intervals = calendar._attendance_intervals_batch(
            start_aware,
            end_aware,
            resources=employee.resource_id,
        ).get(employee.resource_id.id, [])
        hours = sum((stop - start).total_seconds() / 3600.0 for start, stop, _meta in intervals)
        days = len({start.astimezone(tz).date() for start, _stop, _meta in intervals})
        return hours, float(days)

    def _global_public_holiday_hours(self, start_aware, end_aware):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id or self.employee_id.company_id.resource_calendar_id
        if not calendar:
            return 0.0
        scheduled = calendar.get_work_hours_count(
            start_aware, end_aware, compute_leaves=False
        )
        effective = calendar.get_work_hours_count(
            start_aware, end_aware, compute_leaves=True
        )
        return max(0.0, scheduled - effective)

    def _approved_leave_hours(self, start_naive, end_naive, start_aware, end_aware):
        self.ensure_one()
        if "hr.leave" not in self.env.registry.models:
            return 0.0, 0.0
        leaves = self.env["hr.leave"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("state", "=", "validate"),
                ("date_from", "<", end_naive),
                ("date_to", ">", start_naive),
            ]
        )
        calendar = self.employee_id.resource_calendar_id or self.employee_id.company_id.resource_calendar_id
        if not calendar:
            return 0.0, 0.0
        paid = 0.0
        unpaid = 0.0
        for leave in leaves:
            leave_start = max(leave.date_from, start_naive).replace(tzinfo=pytz.UTC)
            leave_end = min(leave.date_to, end_naive).replace(tzinfo=pytz.UTC)
            if leave_end <= leave_start:
                continue
            hours = calendar.get_work_hours_count(
                max(leave_start, start_aware),
                min(leave_end, end_aware),
                compute_leaves=False,
            )
            leave_type = leave.holiday_status_id
            is_unpaid = bool(
                "unpaid" in leave_type._fields and leave_type.unpaid
            )
            if is_unpaid:
                unpaid += hours
            else:
                paid += hours
        return paid, unpaid

    def _recalculate_payable_hours(self):
        for line in self:
            candidate = (
                line.regular_hours
                + line.paid_leave_hours
                + line.public_holiday_hours
                + line.attendance_adjustment_hours
            )
            payable = max(0.0, candidate)
            # Salaried employees are prorated up to their full scheduled period.
            # Hourly employees are paid for all approved regular hours; approved
            # overtime remains a separate earning line.
            if line.pay_basis == "salary" and line.scheduled_hours > 0:
                payable = min(line.scheduled_hours, payable)
            unpaid = max(
                0.0,
                line.scheduled_hours - payable - line.unpaid_leave_hours,
            ) + line.unpaid_leave_hours
            effective_rate = 0.0
            if line.pay_basis == "salary" and line.scheduled_hours > 0:
                effective_rate = line.period_salary / line.scheduled_hours
            elif line.pay_basis == "hourly":
                effective_rate = line.hourly_rate
            super(TTPayrollRunEmployee, line.with_context(tt_payroll_internal_write=True)).write(
                {
                    "payable_hours": payable,
                    "unpaid_hours": unpaid,
                    "effective_hourly_rate": effective_rate,
                }
            )

    def _pull_attendance_snapshot(self):
        Attendance = self.env["hr.attendance"]
        for line in self:
            if not line.run_id.date_start or not line.run_id.date_end:
                continue
            tz, start_aware, end_aware, start_naive, end_naive = line._period_bounds()
            scheduled_hours, scheduled_days = line._scheduled_hours_and_days(
                start_aware, end_aware, tz
            )
            attendances = Attendance.search(
                [
                    ("employee_id", "=", line.employee_id.id),
                    ("check_in", "<", end_naive),
                    "|",
                    ("check_out", "=", False),
                    ("check_out", ">", start_naive),
                ],
                order="check_in",
            )
            completed = attendances.filtered("check_out")
            actual_worked = sum(
                attendance._get_worked_hours_in_range(start_naive, end_naive)
                for attendance in completed
            )
            raw_overtime = sum(completed.mapped("overtime_hours"))
            approved_overtime = sum(completed.mapped("validated_overtime_hours"))
            pending_overtime = max(0.0, raw_overtime - approved_overtime)
            regular_hours = max(0.0, actual_worked - raw_overtime)
            paid_leave, unpaid_leave = line._approved_leave_hours(
                start_naive, end_naive, start_aware, end_aware
            )
            public_holiday = line._global_public_holiday_hours(
                start_aware, end_aware
            )

            attendance_issues = []
            incomplete_count = len(attendances - completed)
            if not line.employee_id.resource_calendar_id:
                attendance_issues.append(_("No employee work schedule is assigned."))
            if incomplete_count:
                attendance_issues.append(
                    _("%s attendance record(s) have no check-out.") % incomplete_count
                )
            if pending_overtime > 0:
                attendance_issues.append(
                    _("%.2f overtime hour(s) are awaiting approval.") % pending_overtime
                )
            if scheduled_hours > 0 and not attendances and paid_leave <= 0 and public_holiday <= 0:
                attendance_issues.append(_("No attendance was found for this scheduled period."))
            preliminary_payable = max(
                0.0,
                regular_hours
                + paid_leave
                + public_holiday
                + line.attendance_adjustment_hours,
            )
            if line.pay_basis == "salary" and scheduled_hours > 0:
                preliminary_payable = min(scheduled_hours, preliminary_payable)
            preliminary_unpaid = max(
                0.0, scheduled_hours - preliminary_payable - unpaid_leave
            ) + unpaid_leave
            if preliminary_unpaid > 0:
                attendance_issues.append(
                    _("%.2f expected hour(s) are currently unpaid or missing.")
                    % preliminary_unpaid
                )

            values = {
                "scheduled_days": scheduled_days,
                "scheduled_hours": scheduled_hours,
                "attendance_record_count": len(attendances),
                "incomplete_attendance_count": incomplete_count,
                "actual_worked_hours": actual_worked,
                "regular_hours": regular_hours,
                "overtime_hours": approved_overtime,
                "pending_overtime_hours": pending_overtime,
                "public_holiday_hours": public_holiday,
                "paid_leave_hours": paid_leave,
                "unpaid_leave_hours": unpaid_leave,
                "attendance_loaded_at": fields.Datetime.now(),
                "attendance_confirmed": False,
                "attendance_status": "needs_attention" if attendance_issues else "ready",
                "attendance_issue_summary": "\n".join(
                    "• %s" % issue for issue in attendance_issues
                ),
            }
            super(TTPayrollRunEmployee, line.with_context(tt_payroll_internal_write=True)).write(values)
            line._recalculate_payable_hours()
        return True

    def _primary_earning_amount(self):
        self.ensure_one()
        return self.effective_hourly_rate * self.payable_hours

    def _prepare_primary_item_values(self):
        self.ensure_one()
        if self.pay_basis == "hourly":
            pay_item = self.env.ref("spx_tt_payroll.pay_item_regular_hours")
            description = _("Regular Hours")
        else:
            pay_item = self.env.ref("spx_tt_payroll.pay_item_basic")
            description = _("Salary")
        return {
            "run_employee_id": self.id,
            "pay_item_id": pay_item.id,
            "description": description,
            "category": "earning",
            "calculation_method": "hours",
            "rate": self.effective_hourly_rate,
            "quantity": self.payable_hours,
            "factor": 1.0,
            "source": "salary",
            "taxable": True,
            "nis_applicable": True,
            "show_on_payslip": True,
            "note": _("Automatically calculated from the attendance snapshot."),
            "sequence": 10,
        }

    def _prepare_overtime_item_values(self):
        self.ensure_one()
        pay_item = self.env.ref("spx_tt_payroll.pay_item_overtime_150")
        return {
            "run_employee_id": self.id,
            "pay_item_id": pay_item.id,
            "description": _("Approved Overtime 1.5×"),
            "category": "earning",
            "calculation_method": "hours",
            "rate": self.effective_hourly_rate,
            "quantity": self.overtime_hours,
            "factor": 1.5,
            "source": "attendance",
            "taxable": True,
            "nis_applicable": True,
            "show_on_payslip": True,
            "note": _("Default overtime factor for the structure phase; review before approval."),
            "sequence": 20,
        }

    def _prepare_recurring_item_values(self, recurring_item, primary_amount):
        pay_item = recurring_item.pay_item_id
        return {
            "run_employee_id": self.id,
            "pay_item_id": pay_item.id,
            "employee_pay_item_id": recurring_item.id,
            "description": pay_item.name,
            "category": pay_item.category,
            "calculation_method": pay_item.calculation_method,
            "rate": recurring_item.amount,
            "quantity": recurring_item.quantity or 1.0,
            "factor": 1.0,
            "percentage": recurring_item.percentage,
            "base_amount": primary_amount,
            "manual_amount": recurring_item.amount * (recurring_item.quantity or 1.0),
            "source": "recurring",
            "taxable": pay_item.taxable,
            "nis_applicable": pay_item.nis_applicable,
            "statutory_code": pay_item.statutory_code,
            "reference": recurring_item.reference,
            "remaining_balance": recurring_item.remaining_balance,
            "show_on_payslip": recurring_item.show_on_payslip,
            "note": recurring_item.note,
            "sequence": pay_item.sequence,
        }

    def _prepare_statutory_item_values(self, xmlid):
        self.ensure_one()
        pay_item = self.env.ref(xmlid)
        return {
            "run_employee_id": self.id,
            "pay_item_id": pay_item.id,
            "description": pay_item.name,
            "category": pay_item.category,
            "calculation_method": "manual",
            "manual_amount": 0.0,
            "source": "statutory",
            "taxable": False,
            "nis_applicable": False,
            "statutory_code": pay_item.statutory_code,
            "show_on_payslip": pay_item.category != "employer",
            "note": _("Automatic statutory line. The verified Trinidad calculation table is added in the statutory phase."),
            "sequence": pay_item.sequence,
        }

    def _load_default_items(self):
        Item = self.env["spx.tt.payroll.run.item"]
        values_list = []
        statutory_xmlids = (
            "spx_tt_payroll.pay_item_paye",
            "spx_tt_payroll.pay_item_employee_nis",
            "spx_tt_payroll.pay_item_health_surcharge",
            "spx_tt_payroll.pay_item_employer_nis",
        )
        for line in self:
            primary = line.item_line_ids.filtered(
                lambda item: item.source in ("basic", "salary")
            )[:1]
            if primary:
                primary_amount = primary.amount
            else:
                primary_values = line._prepare_primary_item_values()
                values_list.append(primary_values)
                primary_amount = line._primary_earning_amount()

            if line.overtime_hours > 0 and not line.item_line_ids.filtered(
                lambda item: item.source == "attendance"
                and item.pay_item_id == self.env.ref("spx_tt_payroll.pay_item_overtime_150")
            ):
                values_list.append(line._prepare_overtime_item_values())

            recurring_items = line.employee_id.tt_recurring_pay_item_ids.filtered(
                lambda item: item.active
                and item.auto_include
                and (not item.start_date or item.start_date <= line.run_id.date_end)
                and (not item.end_date or item.end_date >= line.run_id.date_start)
                and (
                    not item.pay_frequency_ids
                    or line.run_id.pay_frequency_id in item.pay_frequency_ids
                )
            )
            existing_recurring_keys = {
                item.employee_pay_item_id.id
                for item in line.item_line_ids.filtered(
                    lambda payroll_item: payroll_item.source == "recurring"
                    and payroll_item.employee_pay_item_id
                )
            }
            for recurring_item in recurring_items:
                if recurring_item.id not in existing_recurring_keys:
                    values_list.append(
                        line._prepare_recurring_item_values(
                            recurring_item, primary_amount
                        )
                    )

            # Respect any existing statutory item, including a line the payroll
            # officer may already have entered in an earlier Phase 2A payroll.
            existing_statutory_codes = set(
                line.item_line_ids.filtered(
                    lambda item: item.statutory_code != "none"
                ).mapped("statutory_code")
            )
            for xmlid in statutory_xmlids:
                pay_item = self.env.ref(xmlid)
                if pay_item.statutory_code not in existing_statutory_codes:
                    values_list.append(line._prepare_statutory_item_values(xmlid))
        if values_list:
            Item.create(values_list)
        return True

    def _rebuild_attendance_earnings(self):
        for line in self:
            line.item_line_ids.filtered(
                lambda item: item.source in ("basic", "salary", "attendance")
            ).unlink()
            line._load_default_items()
        return True

    def _ensure_basic_pay_line(self):
        """Compatibility name used by Phase 2A's Calculate button."""
        for line in self:
            if not line.item_line_ids.filtered(
                lambda item: item.source in ("basic", "salary")
            ):
                self.env["spx.tt.payroll.run.item"].create(
                    line._prepare_primary_item_values()
                )
            line._load_default_items()
        return True

    def _check_editable(self):
        for line in self:
            if line.run_state in ("approved", "paid", "cancelled"):
                raise UserError(_("Approved, paid, or cancelled payroll calculations are locked."))

    def action_refresh_attendance(self):
        self._check_editable()
        for line in self:
            line._pull_attendance_snapshot()
            line._rebuild_attendance_earnings()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_recalculate_earnings(self):
        self._check_editable()
        for line in self:
            line._recalculate_payable_hours()
            line._rebuild_attendance_earnings()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_confirm_attendance(self):
        self._check_editable()
        for line in self:
            has_exception = bool(
                line.incomplete_attendance_count
                or line.pending_overtime_hours
                or line.unpaid_hours
                or line.attendance_adjustment_hours
            )
            if has_exception and not line.attendance_review_note:
                raise UserError(
                    _("Enter an Attendance Review Note before confirming attendance with exceptions.")
                )
            line.with_context(tt_payroll_internal_write=True).write(
                {"attendance_confirmed": True, "attendance_status": "ready"}
            )
        return True

    def action_refresh_from_employee(self):
        self._check_editable()
        for line in self:
            snapshot = line._employee_snapshot_values(line.employee_id, line.run_id)
            line.with_context(tt_payroll_internal_write=True).write(snapshot)
            line._pull_attendance_snapshot()
            line.item_line_ids.filtered(
                lambda item: item.source in ("basic", "salary", "attendance", "recurring")
            ).unlink()
            line._load_default_items()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_mark_reviewed(self):
        self._check_editable()
        for line in self:
            if line.issue_count:
                raise UserError(
                    _("Resolve the items requiring attention before marking this employee reviewed.")
                )
            line.review_state = "reviewed"
        return True

    def action_place_on_hold(self):
        self._check_editable()
        self.write({"review_state": "on_hold"})
        return True

    def action_include(self):
        self._check_editable()
        self.write({"review_state": "pending"})
        return True

    def action_exclude(self):
        self._check_editable()
        self.write({"review_state": "excluded"})
        return True

    def action_remove_from_run(self):
        self._check_editable()
        if any(line.run_state != "draft" for line in self):
            raise UserError(_("Employees can only be removed while the payroll run is in Draft."))
        return self.unlink()

    def action_open_calculation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Employee Payroll Calculation"),
            "res_model": "spx.tt.payroll.run.employee",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "spx_tt_payroll.view_tt_payroll_run_employee_form"
                    ).id,
                    "form",
                )
            ],
            "res_id": self.id,
            "target": "current",
        }

    def action_open_run(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.run_id.name,
            "res_model": "spx.tt.payroll.run",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("spx_tt_payroll.view_tt_payroll_run_form").id,
                    "form",
                )
            ],
            "res_id": self.run_id.id,
            "target": "current",
        }

    def action_open_employee_profile(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.employee_id.name,
            "res_model": "hr.employee",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("spx_tt_payroll.view_tt_payroll_employee_form").id,
                    "form",
                )
            ],
            "res_id": self.employee_id.id,
            "target": "current",
        }

    def action_open_attendances(self):
        self.ensure_one()
        return self.employee_id.action_tt_open_attendances()

    def write(self, vals):
        if not self.env.context.get("tt_payroll_allow_locked_write"):
            editable_fields = set(vals) - {"message_follower_ids", "message_ids", "activity_ids"}
            if editable_fields:
                self._check_editable()
        result = super().write(vals)
        if (
            "attendance_adjustment_hours" in vals
            and not self.env.context.get("tt_payroll_internal_write")
        ):
            for line in self:
                super(TTPayrollRunEmployee, line.with_context(tt_payroll_internal_write=True)).write(
                    {"attendance_confirmed": False, "attendance_status": "needs_attention"}
                )
                line._recalculate_payable_hours()
                line._rebuild_attendance_earnings()
        return result

    def unlink(self):
        self._check_editable()
        return super().unlink()
