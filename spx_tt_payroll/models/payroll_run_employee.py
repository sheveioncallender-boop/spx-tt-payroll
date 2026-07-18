from datetime import date, datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Official NIBTT earnings classes effective 5 January 2026.
# Amounts are weekly contributions. A None maximum means no upper limit.
NIS_2026_EFFECTIVE_DATE = date(2026, 1, 5)
NIS_2026_CLASSES = (
    ("I", 200.00, 339.99, 867.00, 1472.99, 14.60, 29.20, 2.20),
    ("II", 340.00, 449.99, 1473.00, 1949.99, 21.30, 42.60, 3.20),
    ("III", 450.00, 609.99, 1950.00, 2642.99, 28.60, 57.20, 4.30),
    ("IV", 610.00, 759.99, 2643.00, 3292.99, 37.00, 74.00, 5.56),
    ("V", 760.00, 929.99, 3293.00, 4029.99, 45.60, 91.20, 6.84),
    ("VI", 930.00, 1119.99, 4030.00, 4852.99, 55.40, 110.80, 8.32),
    ("VII", 1120.00, 1299.99, 4853.00, 5632.99, 65.30, 130.60, 9.80),
    ("VIII", 1300.00, 1489.99, 5633.00, 6456.99, 75.30, 150.60, 11.30),
    ("IX", 1490.00, 1709.99, 6457.00, 7409.99, 86.40, 172.80, 12.96),
    ("X", 1710.00, 1909.99, 7410.00, 8276.99, 97.70, 195.40, 14.66),
    ("XI", 1910.00, 2139.99, 8277.00, 9272.99, 109.40, 218.80, 16.42),
    ("XII", 2140.00, 2379.99, 9273.00, 10312.99, 122.00, 244.00, 18.30),
    ("XIII", 2380.00, 2629.99, 10313.00, 11396.99, 135.30, 270.60, 20.30),
    ("XIV", 2630.00, 2919.99, 11397.00, 12652.99, 149.90, 299.80, 22.49),
    ("XV", 2920.00, 3137.99, 12653.00, 13599.99, 163.60, 327.20, 24.55),
    ("XVI", 3138.00, None, 13600.00, None, 169.50, 339.00, 25.43),
)

# Current Trinidad and Tobago individual PAYE and Health Surcharge defaults.
TT_PERSONAL_ALLOWANCE = 90000.00
TT_PENSION_NIS_RELIEF_LIMIT = 60000.00
TT_NIS_RELIEF_PERCENT = 70.0
TT_LOWER_TAX_RATE = 25.0
TT_UPPER_TAX_RATE = 30.0
TT_UPPER_TAX_THRESHOLD = 1000000.00
TT_HEALTH_SURCHARGE_STANDARD = 8.25
TT_HEALTH_SURCHARGE_LOW = 4.80
TT_HEALTH_SURCHARGE_WEEKLY_THRESHOLD = 109.00
TT_HEALTH_SURCHARGE_MONTHLY_THRESHOLD = 469.99


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
    nis_class_display = fields.Char(
        string="NIS Class",
        compute="_compute_statutory_display",
    )
    paye_amount = fields.Monetary(
        string="PAYE",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )
    employee_nis_amount = fields.Monetary(
        string="Employee NIS",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )
    employer_nis_amount = fields.Monetary(
        string="Employer NIS",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )
    health_surcharge_amount = fields.Monetary(
        string="Health Surcharge",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )
    ytd_taxable_earnings = fields.Monetary(
        string="YTD Taxable Earnings",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )
    ytd_paye = fields.Monetary(
        string="YTD PAYE",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )
    ytd_employee_nis = fields.Monetary(
        string="YTD Employee NIS",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )
    ytd_health_surcharge = fields.Monetary(
        string="YTD Health Surcharge",
        currency_field="currency_id",
        compute="_compute_statutory_display",
    )

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
    approved_time_off_count = fields.Integer(string="Approved Time Off")
    pending_time_off_count = fields.Integer(string="Time Off Awaiting Approval")
    pending_time_off_hours = fields.Float(string="Pending Time Off Hours")
    time_off_attendance_overlap_hours = fields.Float(
        string="Attendance / Time Off Conflict Hours"
    )
    time_off_snapshot_ids = fields.One2many(
        "spx.tt.payroll.time.off.snapshot",
        "run_employee_id",
        string="Odoo Time Off Snapshot",
        readonly=True,
    )
    time_off_snapshot_count = fields.Integer(
        string="Time Off",
        compute="_compute_time_off_snapshot_count",
    )
    attendance_adjustment_hours = fields.Float(
        string="Approved Hours Adjustment",
        help="Add or subtract approved payable hours after reviewing missing clock-ins, paid leave, or another payroll exception. Saving this field recalculates Salary or Regular Hours.",
    )
    payable_hours = fields.Float(
        string="Final Payable Hours",
        help="Regular worked hours plus payable leave/public-holiday hours and approved manual adjustments. Overtime is paid separately.",
    )
    missing_hours = fields.Float(string="Missing Hours")
    unpaid_hours = fields.Float(string="Total Unpaid / Missing Hours")
    attendance_loaded_at = fields.Datetime(string="Attendance Pulled At", readonly=True)
    attendance_confirmed = fields.Boolean(string="Attendance Confirmed", copy=False)
    attendance_review_note = fields.Text(
        string="Attendance Review Note",
        help="Explain clocking corrections, paid leave decisions, or accepted unpaid hours.",
    )
    attendance_issue_summary = fields.Text(string="Attendance Issues", readonly=True)
    hours_adjustment_ids = fields.One2many(
        "spx.tt.payroll.hours.adjustment",
        "run_employee_id",
        string="Payable Hours Adjustment History",
        readonly=True,
    )
    hours_adjustment_count = fields.Integer(
        string="Hour Adjustments",
        compute="_compute_hours_adjustment_count",
    )
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
    # Payslip-aligned views of the same payroll items. The underlying category
    # still controls gross and net calculations; these sections only organise
    # the payroll officer's review and the future payslip.
    earning_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="All Earnings",
        domain=[("category", "=", "earning")],
    )
    wage_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Wages",
        domain=[("payslip_section", "=", "wage")],
    )
    addition_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Additions",
        domain=[("payslip_section", "=", "addition")],
    )
    tax_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Taxes",
        domain=[("payslip_section", "=", "tax")],
    )
    deduction_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Deductions",
        domain=[("payslip_section", "=", "deduction")],
    )
    loan_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Loans",
        domain=[("payslip_section", "=", "loan")],
    )
    employer_item_ids = fields.One2many(
        "spx.tt.payroll.run.item",
        "run_employee_id",
        string="Employer Contributions",
        domain=[("payslip_section", "=", "employer")],
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

    @api.depends("hours_adjustment_ids")
    def _compute_hours_adjustment_count(self):
        for line in self:
            line.hours_adjustment_count = len(line.hours_adjustment_ids)

    @api.depends("time_off_snapshot_ids")
    def _compute_time_off_snapshot_count(self):
        for line in self:
            line.time_off_snapshot_count = len(line.time_off_snapshot_ids)

    _sql_constraints = [
        (
            "spx_tt_run_employee_unique",
            "unique(run_id, employee_id)",
            "An employee can only appear once in the same payroll run.",
        )
    ]

    @api.depends(
        "item_line_ids.amount",
        "item_line_ids.statutory_code",
        "item_line_ids.reference",
        "taxable_earnings",
        "run_id.payment_date",
        "run_id.payroll_year",
    )
    def _compute_statutory_display(self):
        for line in self:
            statutory = {
                item.statutory_code: item
                for item in line.item_line_ids
                if item.statutory_code != "none"
            }
            paye = statutory.get("paye")
            employee_nis = statutory.get("employee_nis")
            employer_nis = statutory.get("employer_nis")
            health = statutory.get("health_surcharge")
            line.paye_amount = paye.amount if paye else 0.0
            line.employee_nis_amount = employee_nis.amount if employee_nis else 0.0
            line.employer_nis_amount = employer_nis.amount if employer_nis else 0.0
            line.health_surcharge_amount = health.amount if health else 0.0
            line.nis_class_display = (
                (employee_nis.reference if employee_nis else False)
                or (employer_nis.reference if employer_nis else False)
                or False
            )
            ytd = line._get_ytd_values(include_current=True)
            line.ytd_taxable_earnings = ytd["taxable"]
            line.ytd_paye = ytd["paye"]
            line.ytd_employee_nis = ytd["employee_nis"]
            line.ytd_health_surcharge = ytd["health_surcharge"]

    def _get_statutory_profile(self):
        self.ensure_one()
        return self.env["spx.tt.employee.statutory.profile"].search(
            [("employee_id", "=", self.employee_id.id)], limit=1
        )

    def _employee_age_on_payment_date(self):
        self.ensure_one()
        birthday = self.employee_id.birthday
        payment_date = self.run_id.payment_date or self.run_id.date_end
        if not birthday or not payment_date:
            return False
        return payment_date.year - birthday.year - (
            (payment_date.month, payment_date.day) < (birthday.month, birthday.day)
        )

    def _normal_frequency_code(self):
        self.ensure_one()
        code = self.run_id.pay_frequency_id.code if self.run_id.pay_frequency_id else ""
        if code == "OFF_CYCLE" and self.pay_frequency_id:
            code = self.pay_frequency_id.code
        return code

    def _annual_period_count(self):
        self.ensure_one()
        return {
            "WEEKLY": 52,
            "FORTNIGHTLY": 26,
            "SEMI_MONTHLY": 24,
            "MONTHLY": 12,
        }.get(self._normal_frequency_code(), 12)

    def _period_index_in_year(self):
        self.ensure_one()
        payment_date = self.run_id.payment_date or self.run_id.date_end
        if not payment_date:
            return 1
        code = self._normal_frequency_code()
        if code == "MONTHLY":
            return payment_date.month
        if code == "SEMI_MONTHLY":
            return (payment_date.month - 1) * 2 + (1 if payment_date.day <= 15 else 2)
        year_start = date(payment_date.year, 1, 1)
        days_elapsed = (payment_date - year_start).days
        if code == "WEEKLY":
            return min(52, days_elapsed // 7 + 1)
        if code == "FORTNIGHTLY":
            return min(26, days_elapsed // 14 + 1)
        return 1

    def _statutory_week_count(self):
        self.ensure_one()
        return max(self.run_id.monday_count or self.run_id.period_week_count or 1, 1)

    def _equivalent_statutory_earnings(self, earnings):
        self.ensure_one()
        code = self._normal_frequency_code()
        if code == "MONTHLY":
            return {"basis": "monthly", "amount": earnings}
        if code == "SEMI_MONTHLY":
            return {"basis": "monthly", "amount": earnings * 2.0}
        if code == "FORTNIGHTLY":
            return {"basis": "weekly", "amount": earnings / 2.0}
        if code == "WEEKLY":
            return {"basis": "weekly", "amount": earnings}
        weeks = max(self.run_id.period_week_count or 1, 1)
        return {"basis": "weekly", "amount": earnings / weeks}

    def _find_nis_class(self, earnings):
        self.ensure_one()
        equivalent = self._equivalent_statutory_earnings(earnings)
        amount = equivalent["amount"]
        basis = equivalent["basis"]
        for row in NIS_2026_CLASSES:
            name, weekly_min, weekly_max, monthly_min, monthly_max, employee, employer, class_z = row
            minimum = monthly_min if basis == "monthly" else weekly_min
            maximum = monthly_max if basis == "monthly" else weekly_max
            if amount >= minimum and (maximum is None or amount <= maximum):
                return {
                    "name": name,
                    "basis": basis,
                    "equivalent_earnings": amount,
                    "employee_weekly": employee,
                    "employer_weekly": employer,
                    "class_z_weekly": class_z,
                }
        return False

    def _get_ytd_values(self, include_current=False):
        self.ensure_one()
        year = self.run_id.payroll_year or (
            self.run_id.payment_date or self.run_id.date_end or fields.Date.context_today(self)
        ).year
        profile = self._get_statutory_profile()
        values = {
            "taxable": 0.0,
            "paye": 0.0,
            "employee_nis": 0.0,
            "health_surcharge": 0.0,
            "period_count": 0,
        }
        if profile and profile.opening_ytd_year == year:
            values.update(
                {
                    "taxable": profile.opening_taxable_earnings,
                    "paye": profile.opening_paye,
                    "employee_nis": profile.opening_employee_nis,
                    "health_surcharge": profile.opening_health_surcharge,
                    "period_count": profile.opening_period_count,
                }
            )
        previous = self.search(
            [
                ("id", "!=", self.id),
                ("employee_id", "=", self.employee_id.id),
                ("company_id", "=", self.company_id.id),
                ("run_id.payroll_year", "=", year),
                ("run_id.payment_date", "<=", self.run_id.payment_date),
                ("run_id.state", "in", ["approved", "paid"]),
            ]
        )
        values["taxable"] += sum(previous.mapped("taxable_earnings"))
        values["period_count"] += len(previous)
        for line in previous:
            for item in line.item_line_ids.filtered(lambda x: x.statutory_code != "none"):
                if item.statutory_code == "paye":
                    values["paye"] += item.amount
                elif item.statutory_code == "employee_nis":
                    values["employee_nis"] += item.amount
                elif item.statutory_code == "health_surcharge":
                    values["health_surcharge"] += item.amount
        if include_current:
            values["taxable"] += self.taxable_earnings
            values["period_count"] += 1
            for item in self.item_line_ids.filtered(lambda x: x.statutory_code != "none"):
                if item.statutory_code == "paye":
                    values["paye"] += item.amount
                elif item.statutory_code == "employee_nis":
                    values["employee_nis"] += item.amount
                elif item.statutory_code == "health_surcharge":
                    values["health_surcharge"] += item.amount
        return values

    def _set_statutory_line(self, code, amount, reference=False, note=False):
        self.ensure_one()
        lines = self.item_line_ids.filtered(lambda item: item.statutory_code == code)
        if not lines:
            return
        line = lines[0]
        if len(lines) > 1:
            lines[1:].unlink()
        line.write(
            {
                "calculation_method": "manual",
                "manual_amount": self.currency_id.round(max(0.0, amount)),
                "reference": reference or False,
                "note": note or False,
                "source": "statutory",
            }
        )

    def _calculate_annual_income_tax(self, annual_chargeable):
        """Retained for reporting and backward-compatible extensions."""
        lower = min(max(annual_chargeable, 0.0), TT_UPPER_TAX_THRESHOLD)
        upper = max(annual_chargeable - TT_UPPER_TAX_THRESHOLD, 0.0)
        return lower * TT_LOWER_TAX_RATE / 100.0 + upper * TT_UPPER_TAX_RATE / 100.0

    def _calculate_period_income_tax(self, period_chargeable, annual_periods):
        """Calculate PAYE for one payroll period.

        The annual TT$1,000,000 tax-band threshold is apportioned across the
        employee's normal number of pay periods. The final PAYE amount is
        rounded only when it is written to the statutory payroll line.
        """
        annual_periods = max(annual_periods or 1, 1)
        period_threshold = TT_UPPER_TAX_THRESHOLD / annual_periods
        lower = min(max(period_chargeable, 0.0), period_threshold)
        upper = max(period_chargeable - period_threshold, 0.0)
        return lower * TT_LOWER_TAX_RATE / 100.0 + upper * TT_UPPER_TAX_RATE / 100.0

    def _calculate_statutory_items(self):
        for line in self:
            if line.run_state in ("approved", "paid", "cancelled"):
                continue
            earnings = line.item_line_ids.filtered(lambda item: item.category == "earning")
            gross_earnings = sum(earnings.mapped("amount"))
            taxable_earnings = sum(
                earnings.filtered(lambda item: not item.exclude_from_paye).mapped("amount")
            )
            nis_earnings = sum(earnings.filtered("nis_applicable").mapped("amount"))
            profile = line._get_statutory_profile()
            age = line._employee_age_on_payment_date()
            weeks = line._statutory_week_count()
            payment_date = line.run_id.payment_date or line.run_id.date_end
            nis_table_available = bool(payment_date and payment_date >= NIS_2026_EFFECTIVE_DATE)
            nis_class = (
                line._find_nis_class(nis_earnings)
                if nis_earnings > 0 and nis_table_available
                else False
            )
            nis_reference = False
            employee_nis = 0.0
            employer_nis = 0.0
            employee_weekly = 0.0

            if line.nis_exempt:
                nis_note = _("NIS exempt on the employee payroll profile.")
            elif not nis_table_available:
                nis_note = _("Automatic NIS is unavailable because this build contains the table effective 5 January 2026 and the payroll date is earlier.")
                nis_reference = _("Rate table required")
            elif not nis_class:
                nis_note = _("No NIS contribution: insurable earnings are below Class I or zero.")
                nis_reference = _("Below Class I") if nis_earnings > 0 else False
            else:
                class_z = bool(
                    (age is not False and (age < 16 or age >= 65))
                    or (profile and profile.retirement_pension_recipient)
                )
                nis_reference = _("Class Z / Class %s") % nis_class["name"] if class_z else _("Class %s") % nis_class["name"]
                if class_z:
                    employer_nis = nis_class["class_z_weekly"] * weeks
                    nis_note = _(
                        "Class Z employer-only NIS: %s week(s) × TT$%.2f. Equivalent %s earnings TT$%.2f."
                    ) % (weeks, nis_class["class_z_weekly"], nis_class["basis"], nis_class["equivalent_earnings"])
                else:
                    employee_weekly = nis_class["employee_weekly"]
                    employee_nis = employee_weekly * weeks
                    employer_nis = nis_class["employer_weekly"] * weeks
                    nis_note = _(
                        "NIS Class %s: %s week(s). Employee TT$%.2f weekly; employer TT$%.2f weekly. Equivalent %s earnings TT$%.2f."
                    ) % (
                        nis_class["name"],
                        weeks,
                        nis_class["employee_weekly"],
                        nis_class["employer_weekly"],
                        nis_class["basis"],
                        nis_class["equivalent_earnings"],
                    )
            line._set_statutory_line("employee_nis", employee_nis, nis_reference, nis_note)
            line._set_statutory_line("employer_nis", employer_nis, nis_reference, nis_note)

            health_exempt = bool(
                line.health_surcharge_exempt
                or (age is not False and (age < 16 or age >= 60))
                or (profile and profile.pension_only_income)
            )
            # PAYE exclusions do not reduce Health Surcharge emoluments. The
            # user-facing exception is intentionally PAYE-only.
            equivalent = line._equivalent_statutory_earnings(gross_earnings)
            if health_exempt or gross_earnings <= 0:
                health_amount = 0.0
                health_note = _("Health Surcharge exempt or no emoluments in this pay period.")
            else:
                high_rate = (
                    equivalent["amount"] > TT_HEALTH_SURCHARGE_MONTHLY_THRESHOLD
                    if equivalent["basis"] == "monthly"
                    else equivalent["amount"] > TT_HEALTH_SURCHARGE_WEEKLY_THRESHOLD
                )
                health_rate = TT_HEALTH_SURCHARGE_STANDARD if high_rate else TT_HEALTH_SURCHARGE_LOW
                health_amount = health_rate * weeks
                health_note = _(
                    "Health Surcharge: %s week(s) × TT$%.2f. Equivalent %s emoluments TT$%.2f."
                ) % (weeks, health_rate, equivalent["basis"], equivalent["amount"])
            line._set_statutory_line("health_surcharge", health_amount, _("%s week(s)") % weeks, health_note)

            if profile and profile.paye_exempt:
                paye_amount = 0.0
                paye_note = _("PAYE exempt on the employee statutory profile.")
            elif taxable_earnings <= 0:
                paye_amount = 0.0
                paye_note = _("No PAYE because taxable earnings are zero.")
            else:
                # Trinidad PAYE is calculated from the employee's PAYE-taxable
                # earnings for the current pay period. Salary, overtime, and
                # additions are taxable by default; only lines deliberately
                # marked Exclude from PAYE are removed from this earnings base.
                annual_periods = line._annual_period_count()
                resident = profile.resident if profile else True
                annual_personal_allowance = 0.0
                if resident:
                    annual_personal_allowance = (
                        profile.personal_allowance_override
                        if profile and profile.personal_allowance_override > 0
                        else TT_PERSONAL_ALLOWANCE
                    )
                period_personal_allowance = annual_personal_allowance / annual_periods

                annual_pension = (
                    profile.approved_pension_annuity_annual if profile else 0.0
                )
                period_pension = annual_pension / annual_periods
                period_nis_relief = (
                    employee_nis * TT_NIS_RELIEF_PERCENT / 100.0
                )
                period_combined_relief_cap = (
                    TT_PENSION_NIS_RELIEF_LIMIT / annual_periods
                )
                period_pension_nis_relief = min(
                    period_combined_relief_cap,
                    period_pension + period_nis_relief,
                )

                annual_other_deductions = (
                    profile.approved_other_deductions_annual if profile else 0.0
                )
                period_other_deductions = annual_other_deductions / annual_periods
                period_deductions = (
                    period_personal_allowance
                    + period_pension_nis_relief
                    + period_other_deductions
                )
                period_chargeable = max(taxable_earnings - period_deductions, 0.0)

                annual_tax_credits = (
                    profile.approved_tax_credits_annual if profile else 0.0
                )
                period_tax_credits = annual_tax_credits / annual_periods
                gross_period_tax = line._calculate_period_income_tax(
                    period_chargeable, annual_periods
                )
                paye_amount = max(gross_period_tax - period_tax_credits, 0.0)
                paye_note = _(
                    "Automatic period PAYE. Taxable earnings TT$%.2f; period personal allowance TT$%.2f; 70%% NIS relief TT$%.2f; pension/NIS relief used TT$%.2f; other TD1 deductions TT$%.2f; chargeable income TT$%.2f; tax credits TT$%.2f; PAYE TT$%.2f."
                ) % (
                    taxable_earnings,
                    period_personal_allowance,
                    period_nis_relief,
                    period_pension_nis_relief,
                    period_other_deductions,
                    period_chargeable,
                    period_tax_credits,
                    paye_amount,
                )
            line._set_statutory_line(
                "paye", paye_amount, _("Period calculation"), paye_note
            )
        return True

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
        "item_line_ids.exclude_from_paye",
        "item_line_ids.nis_applicable",
    )
    def _compute_totals(self):
        for line in self:
            earnings = line.item_line_ids.filtered(lambda item: item.category == "earning")
            deductions = line.item_line_ids.filtered(lambda item: item.category == "deduction")
            employer_items = line.item_line_ids.filtered(lambda item: item.category == "employer")
            line.gross_pay = sum(earnings.mapped("amount"))
            line.taxable_earnings = sum(
                earnings.filtered(lambda item: not item.exclude_from_paye).mapped("amount")
            )
            line.nis_insurable_earnings = sum(
                earnings.filtered("nis_applicable").mapped("amount")
            )
            line.total_deductions = sum(deductions.mapped("amount"))
            line.employer_contribution_total = sum(employer_items.mapped("amount"))
            line.net_pay = line.gross_pay - line.total_deductions

    def _get_attention_items(self):
        """Return clear, actionable payroll issues for this employee calculation."""
        self.ensure_one()
        items = []

        def add(code, title, detail, action_kind, action_label, sequence):
            items.append(
                {
                    "code": code,
                    "title": title,
                    "detail": detail,
                    "action_kind": action_kind,
                    "action_label": action_label,
                    "sequence": sequence,
                }
            )

        if not self.pay_basis:
            add(
                "missing_pay_basis",
                _("Pay basis is missing"),
                _("Select whether the employee is salaried or hourly paid."),
                "employee_profile",
                _("Open Employee Profile"),
                10,
            )
        if not self.pay_frequency_id:
            add(
                "missing_pay_frequency",
                _("Pay frequency is missing"),
                _("Select weekly, fortnightly, semi-monthly, monthly, or off-cycle."),
                "employee_profile",
                _("Open Employee Profile"),
                20,
            )
        if self.pay_basis == "salary" and self.salary_amount <= 0:
            add(
                "missing_salary",
                _("Salary is missing"),
                _("Enter the employee's normal monthly salary."),
                "employee_profile",
                _("Enter Salary"),
                30,
            )
        if self.pay_basis == "hourly" and self.hourly_rate <= 0:
            add(
                "missing_hourly_rate",
                _("Hourly rate is missing"),
                _("Enter the employee's normal hourly rate."),
                "employee_profile",
                _("Enter Hourly Rate"),
                40,
            )
        if not self.bir_number:
            add(
                "missing_bir",
                _("BIR number is missing"),
                _("Complete the employee's Trinidad statutory information."),
                "statutory_profile",
                _("Open Statutory Details"),
                50,
            )
        if not self.nis_exempt and not self.nis_number:
            add(
                "missing_nis",
                _("NIS number is missing"),
                _("Enter the employee's NIS number or confirm the applicable exemption."),
                "statutory_profile",
                _("Open Statutory Details"),
                60,
            )
        if self.payment_method == "bank" and not self.bank_name:
            add(
                "missing_bank",
                _("Bank name is missing"),
                _("Complete the employee's bank payment information."),
                "employee_profile",
                _("Open Banking Details"),
                70,
            )
        if self.payment_method == "bank" and not self.bank_account_number:
            add(
                "missing_bank_account",
                _("Bank account number is missing"),
                _("Complete the employee's bank payment information."),
                "employee_profile",
                _("Open Banking Details"),
                80,
            )

        if self.attendance_status == "not_loaded":
            add(
                "attendance_not_loaded",
                _("Attendance has not been pulled"),
                _("Pull the employee's current Odoo Attendance and Time Off records for this payroll period."),
                "refresh_attendance",
                _("Pull Attendance & Time Off"),
                100,
            )
        else:
            if not self.employee_id.resource_calendar_id:
                add(
                    "missing_work_schedule",
                    _("Work schedule is missing"),
                    _("Assign the employee's normal Odoo work schedule."),
                    "employee_profile",
                    _("Open Employee Profile"),
                    110,
                )
            if self.incomplete_attendance_count:
                add(
                    "missing_checkout",
                    _("Attendance record has no check-out"),
                    _("Correct the incomplete check-in/check-out record in Odoo Attendances."),
                    "attendances",
                    _("Review Attendances"),
                    120,
                )
            if self.pending_overtime_hours > 0:
                add(
                    "pending_overtime",
                    _("Overtime is awaiting approval"),
                    _("Review and approve the employee's overtime before confirming payroll hours."),
                    "attendances",
                    _("Review Attendances"),
                    130,
                )
            if self.pending_time_off_count:
                add(
                    "pending_time_off",
                    _("Time Off is awaiting approval"),
                    _("Approve or refuse the pending Odoo Time Off request before confirming payroll hours."),
                    "time_off",
                    _("Review Time Off"),
                    135,
                )
            if self.time_off_attendance_overlap_hours > 0.005:
                add(
                    "time_off_attendance_conflict",
                    _("Attendance overlaps approved Time Off"),
                    _("The employee has clocked hours during approved paid or unpaid Time Off. Review the Odoo records before confirming payroll."),
                    "time_off",
                    _("Review Time Off"),
                    137,
                )
            adjustment_recorded = bool(self.hours_adjustment_ids)
            no_attendance = bool(
                self.scheduled_hours > 0
                and self.attendance_record_count == 0
                and self.paid_leave_hours <= 0
                and self.public_holiday_hours <= 0
            )
            if no_attendance and not adjustment_recorded:
                add(
                    "no_attendance",
                    _("No attendance was found for the period"),
                    _("Review the employee's clock records. If the department confirms the hours, use Adjust Payable Hours and record the reason."),
                    "attendances",
                    _("Review Attendances"),
                    140,
                )
            if self.missing_hours > 0.005:
                add(
                    "payable_hours_short",
                    _("Payable hours are below expected hours"),
                    _("Review missing time, paid leave, or apply an approved hours adjustment with a reason."),
                    "adjust_hours",
                    _("Adjust Payable Hours"),
                    150,
                )
            if not self.attendance_confirmed:
                add(
                    "attendance_not_confirmed",
                    _("Attendance has not been confirmed"),
                    _("Confirm the attendance snapshot after all clocking issues and approved adjustments have been reviewed."),
                    "confirm_attendance",
                    _("Confirm Attendance"),
                    160,
                )

        if not self.item_line_ids.filtered(lambda item: item.category == "earning"):
            add(
                "missing_earnings",
                _("No earnings have been generated"),
                _("Recalculate Salary or Regular Hours and reload automatic additions."),
                "recalculate",
                _("Recalculate Pay"),
                200,
            )
        required_statutory = {"paye", "employee_nis", "health_surcharge", "employer_nis"}
        current_statutory = set(
            self.item_line_ids.filtered(
                lambda item: item.statutory_code != "none"
            ).mapped("statutory_code")
        )
        if required_statutory - current_statutory:
            add(
                "missing_statutory_lines",
                _("Standard statutory lines are missing"),
                _("Recalculate PAYE, Employee NIS, Employer NIS, and Health Surcharge."),
                "recalculate",
                _("Recalculate Pay"),
                210,
            )
        if self.net_pay < 0:
            add(
                "negative_net_pay",
                _("Net pay is negative"),
                _("Review taxes, deductions, loans, and manual payroll items before approval."),
                "calculation",
                _("Review Calculation"),
                220,
            )
        return items

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
        "attendance_record_count",
        "incomplete_attendance_count",
        "pending_overtime_hours",
        "pending_time_off_count",
        "time_off_attendance_overlap_hours",
        "scheduled_hours",
        "paid_leave_hours",
        "public_holiday_hours",
        "missing_hours",
        "unpaid_hours",
        "hours_adjustment_ids",
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
        for line in self:
            issues = line._get_attention_items()
            line.issue_count = len(issues)
            line.issue_summary = "\n".join(
                "• %s" % issue["title"] for issue in issues
            )
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

    def _payroll_expected_hours(self, calendar_hours=0.0):
        """Return the standard expected hours used to prorate this payroll.

        Trinidad payroll users commonly define a 40-hour week as 160 hours
        monthly. We therefore use the employee payroll profile rather than the
        varying count of weekdays in a calendar month. Odoo's work schedule is
        still used for attendance, leave, holidays, and off-cycle periods.
        """
        self.ensure_one()
        weekly_hours = self.normal_hours_per_week or 0.0
        code = self.run_id.pay_frequency_id.code if self.run_id.pay_frequency_id else ""
        frequency_weeks = {
            "WEEKLY": 1.0,
            "FORTNIGHTLY": 2.0,
            "SEMI_MONTHLY": 2.0,
            "MONTHLY": 4.0,
        }
        if code in frequency_weeks and weekly_hours > 0:
            return weekly_hours * frequency_weeks[code]
        return calendar_hours

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

    def _public_holiday_hours_in_range(self, start_aware, end_aware):
        """Return global public-holiday hours inside a smaller Time Off range."""
        self.ensure_one()
        if end_aware <= start_aware:
            return 0.0
        return self._global_public_holiday_hours(start_aware, end_aware)

    @api.model
    def _attendance_overlap_hours(self, attendances, leave_start, leave_end):
        """Return raw overlap between completed attendance and a Time Off interval."""
        overlap = 0.0
        for attendance in attendances.filtered("check_out"):
            attendance_start = max(attendance.check_in, leave_start)
            attendance_end = min(attendance.check_out, leave_end)
            if attendance_end > attendance_start:
                overlap += (attendance_end - attendance_start).total_seconds() / 3600.0
        return overlap

    def _collect_time_off_snapshot(
        self,
        start_naive,
        end_naive,
        start_aware,
        end_aware,
        completed_attendances,
    ):
        """Read Odoo Time Off and return payroll totals plus immutable snapshot rows.

        Odoo's Time Off type decides paid versus unpaid through the standard
        ``unpaid`` flag. Only fully approved requests affect payable hours.
        Pending requests are shown as attention items and are not paid.
        """
        self.ensure_one()
        Leave = self.env["hr.leave"].sudo()
        leaves = Leave.search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("state", "in", ["confirm", "validate1", "validate"]),
                ("date_from", "<", end_naive),
                ("date_to", ">", start_naive),
            ],
            order="date_from, id",
        )
        calendar = (
            self.employee_id.resource_calendar_id
            or self.employee_id.company_id.resource_calendar_id
        )
        totals = {
            "paid": 0.0,
            "unpaid": 0.0,
            "approved_count": 0,
            "pending_count": 0,
            "pending_hours": 0.0,
            "attendance_overlap": 0.0,
            "unpaid_overlap": 0.0,
            "snapshot_values": [],
        }
        if not calendar:
            return totals

        for leave in leaves:
            if not leave.date_from or not leave.date_to:
                continue
            leave_start_naive = max(leave.date_from, start_naive)
            leave_end_naive = min(leave.date_to, end_naive)
            if leave_end_naive <= leave_start_naive:
                continue
            leave_start = leave_start_naive.replace(tzinfo=pytz.UTC)
            leave_end = leave_end_naive.replace(tzinfo=pytz.UTC)
            scheduled_hours = calendar.get_work_hours_count(
                max(leave_start, start_aware),
                min(leave_end, end_aware),
                compute_leaves=False,
            )
            public_holiday_hours = self._public_holiday_hours_in_range(
                max(leave_start, start_aware), min(leave_end, end_aware)
            )
            scheduled_hours = max(0.0, scheduled_hours - public_holiday_hours)
            overlap_hours = min(
                scheduled_hours,
                self._attendance_overlap_hours(
                    completed_attendances, leave_start_naive, leave_end_naive
                ),
            )
            approved = leave.state == "validate"
            unpaid = bool(leave.holiday_status_id.unpaid)
            if not approved:
                treatment = "pending"
                payroll_hours = 0.0
                totals["pending_count"] += 1
                totals["pending_hours"] += scheduled_hours
                note = _("Awaiting Odoo Time Off approval; not applied to payroll.")
            elif unpaid:
                treatment = "unpaid"
                payroll_hours = 0.0
                totals["approved_count"] += 1
                totals["unpaid"] += scheduled_hours
                totals["unpaid_overlap"] += overlap_hours
                note = _("Approved unpaid Time Off; these hours reduce payable time.")
            else:
                treatment = "paid"
                payroll_hours = max(0.0, scheduled_hours - overlap_hours)
                totals["approved_count"] += 1
                totals["paid"] += payroll_hours
                note = _("Approved paid Time Off added to payable hours.")
            if approved:
                totals["attendance_overlap"] += overlap_hours
            totals["snapshot_values"].append(
                {
                    "run_employee_id": self.id,
                    "leave_id": leave.id,
                    "leave_type_id": leave.holiday_status_id.id,
                    "date_from": leave_start_naive,
                    "date_to": leave_end_naive,
                    "approval_state": "approved" if approved else "pending",
                    "payroll_treatment": treatment,
                    "scheduled_hours": scheduled_hours,
                    "attendance_overlap_hours": overlap_hours,
                    "payroll_hours": payroll_hours,
                    "note": note,
                }
            )
        return totals

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
            missing = max(
                0.0,
                line.scheduled_hours - payable - line.unpaid_leave_hours,
            )
            unpaid = missing + line.unpaid_leave_hours
            effective_rate = 0.0
            if line.pay_basis == "salary" and line.scheduled_hours > 0:
                effective_rate = line.period_salary / line.scheduled_hours
            elif line.pay_basis == "hourly":
                effective_rate = line.hourly_rate
            super(TTPayrollRunEmployee, line.with_context(tt_payroll_internal_write=True)).write(
                {
                    "payable_hours": payable,
                    "missing_hours": missing,
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
            calendar_hours, calendar_days = line._scheduled_hours_and_days(
                start_aware, end_aware, tz
            )
            scheduled_hours = line._payroll_expected_hours(calendar_hours)
            scheduled_days = (
                scheduled_hours / line.normal_hours_per_day
                if line.normal_hours_per_day
                else calendar_days
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
            time_off = line._collect_time_off_snapshot(
                start_naive,
                end_naive,
                start_aware,
                end_aware,
                completed,
            )
            paid_leave = time_off["paid"]
            unpaid_leave = time_off["unpaid"]
            regular_hours = max(0.0, regular_hours - time_off["unpaid_overlap"])
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
            if time_off["pending_count"]:
                attendance_issues.append(
                    _("%s Odoo Time Off request(s) are awaiting approval.")
                    % time_off["pending_count"]
                )
            if time_off["attendance_overlap"] > 0.005:
                attendance_issues.append(
                    _("%.2f attendance hour(s) overlap approved Time Off.")
                    % time_off["attendance_overlap"]
                )
            if (
                scheduled_hours > 0
                and not attendances
                and paid_leave <= 0
                and unpaid_leave <= 0
                and public_holiday <= 0
            ):
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
            preliminary_missing = max(
                0.0, scheduled_hours - preliminary_payable - unpaid_leave
            )
            if preliminary_missing > 0:
                attendance_issues.append(
                    _("%.2f expected hour(s) are currently missing.")
                    % preliminary_missing
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
                "approved_time_off_count": time_off["approved_count"],
                "pending_time_off_count": time_off["pending_count"],
                "pending_time_off_hours": time_off["pending_hours"],
                "time_off_attendance_overlap_hours": time_off["attendance_overlap"],
                "attendance_loaded_at": fields.Datetime.now(),
                "attendance_confirmed": False,
                "attendance_status": "needs_attention" if attendance_issues else "ready",
                "attendance_issue_summary": "\n".join(
                    "• %s" % issue for issue in attendance_issues
                ),
            }
            line.time_off_snapshot_ids.sudo().unlink()
            if time_off["snapshot_values"]:
                self.env["spx.tt.payroll.time.off.snapshot"].sudo().create(
                    time_off["snapshot_values"]
                )
            super(TTPayrollRunEmployee, line.with_context(tt_payroll_internal_write=True)).write(values)
            line._recalculate_payable_hours()
        return True

    def _primary_earning_amount(self):
        """Return the exact primary wage rounded only at the final amount.

        A salaried employee's hourly equivalent can contain more than two
        decimal places. Using a Monetary rate on the payroll item rounds that
        equivalent too early (for example 9500 / 160 becomes 59.38), which
        incorrectly produces 9500.80. Calculate from the period salary ratio
        and round only the final wage amount.
        """
        self.ensure_one()
        if self.pay_basis == "salary":
            if self.scheduled_hours <= 0 or self.period_salary <= 0:
                return 0.0
            payable_ratio = min(
                1.0,
                max(0.0, self.payable_hours) / self.scheduled_hours,
            )
            return self.currency_id.round(self.period_salary * payable_ratio)
        return self.currency_id.round(
            max(0.0, self.hourly_rate) * max(0.0, self.payable_hours)
        )

    def _prepare_primary_item_values(self):
        self.ensure_one()
        primary_amount = self._primary_earning_amount()
        if self.pay_basis == "hourly":
            pay_item = self.env.ref("spx_tt_payroll.pay_item_regular_hours")
            description = _("Regular Hours")
            calculation_method = "hours"
            manual_amount = 0.0
        else:
            pay_item = self.env.ref("spx_tt_payroll.pay_item_basic")
            description = _("Salary")
            # Keep the displayed equivalent rate and payable hours for review,
            # but use the exact prorated salary as the line total. This avoids
            # rounding the hourly equivalent before multiplying by hours.
            calculation_method = "manual"
            manual_amount = primary_amount
        return {
            "run_employee_id": self.id,
            "pay_item_id": pay_item.id,
            "description": description,
            "category": "earning",
            "calculation_method": calculation_method,
            "rate": self.effective_hourly_rate,
            "quantity": self.payable_hours,
            "manual_amount": manual_amount,
            "factor": 1.0,
            "source": "salary",
            "taxable": True,
            "exclude_from_paye": False,
            "nis_applicable": True,
            "show_on_payslip": True,
            "note": _(
                "Automatically calculated from final payable hours. Salary is prorated from the full period salary and rounded only at the final amount."
            ),
            "sequence": 10,
        }

    def _prepare_overtime_item_values(self):
        self.ensure_one()
        pay_item = self.env.ref("spx_tt_payroll.pay_item_overtime_150")
        calculation_method = "hours"
        manual_amount = 0.0
        if self.pay_basis == "salary" and self.scheduled_hours > 0:
            exact_rate = self.period_salary / self.scheduled_hours
            manual_amount = self.currency_id.round(
                exact_rate * self.overtime_hours * 1.5
            )
            calculation_method = "manual"
        return {
            "run_employee_id": self.id,
            "pay_item_id": pay_item.id,
            "description": _("Approved Overtime 1.5×"),
            "category": "earning",
            "calculation_method": calculation_method,
            "rate": self.effective_hourly_rate,
            "quantity": self.overtime_hours,
            "manual_amount": manual_amount,
            "factor": 1.5,
            "source": "attendance",
            "taxable": True,
            "exclude_from_paye": False,
            "nis_applicable": True,
            "show_on_payslip": True,
            "note": _(
                "Calculated from the exact payroll hourly equivalent and rounded only at the final amount."
            ),
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
            "taxable": not recurring_item.exclude_from_paye,
            "exclude_from_paye": recurring_item.exclude_from_paye,
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
            "exclude_from_paye": False,
            "nis_applicable": False,
            "statutory_code": pay_item.statutory_code,
            "show_on_payslip": pay_item.category != "employer",
            "note": _("Automatic statutory line. Select Recalculate Pay whenever earnings or attendance changes."),
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
            primary_candidates = line.item_line_ids.filtered(
                lambda item: item.source in ("basic", "salary")
                or item.pay_item_id.code in ("BASIC", "REGULAR_HOURS")
            )
            # Salary/Regular Hours is controlled only by the attendance snapshot.
            # Remove every legacy, manual, or recurring base-wage row before
            # creating the single current system line. This guarantees that zero
            # payable hours produces zero Salary and prevents duplicated wages.
            if primary_candidates:
                primary_candidates.unlink()
            primary_values = line._prepare_primary_item_values()
            values_list.append(primary_values)
            primary_amount = line._primary_earning_amount()

            if line.overtime_hours > 0 and not line.item_line_ids.filtered(
                lambda item: item.source == "attendance"
                and item.pay_item_id == self.env.ref("spx_tt_payroll.pay_item_overtime_150")
            ):
                values_list.append(line._prepare_overtime_item_values())

            attendance_wage_codes = {
                "BASIC",
                "REGULAR_HOURS",
                "OT150",
                "OT200",
                "PUBLIC_HOLIDAY",
            }
            recurring_items = line.employee_id.tt_recurring_pay_item_ids.filtered(
                lambda item: item.active
                and item.auto_include
                and item.pay_item_id.code not in attendance_wage_codes
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
        self._calculate_statutory_items()
        return True

    def _rebuild_attendance_earnings(self):
        for line in self:
            line.item_line_ids.filtered(
                lambda item: item.source in ("basic", "salary", "attendance")
                or item.pay_item_id.code in ("BASIC", "REGULAR_HOURS")
            ).unlink()
            line._load_default_items()
        return True

    def _ensure_basic_pay_line(self):
        """Compatibility name used by Phase 2A's Calculate button."""
        for line in self:
            line._load_default_items()
        return True

    def _check_editable(self):
        for line in self:
            if line.run_state in ("approved", "paid", "cancelled"):
                raise UserError(_("Approved, paid, or cancelled payroll calculations are locked."))

    def action_open_attention_items(self):
        self.ensure_one()
        items = self._get_attention_items()
        if not items:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Payroll calculation is ready"),
                    "message": _("There are no unresolved items for this employee."),
                    "type": "success",
                    "sticky": False,
                },
            }
        wizard = self.env["spx.tt.payroll.attention.wizard"].create_for_calculation(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("Items Needing Attention"),
            "res_model": "spx.tt.payroll.attention.wizard",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "spx_tt_payroll.view_tt_payroll_attention_wizard_form"
                    ).id,
                    "form",
                )
            ],
            "res_id": wizard.id,
            "target": "new",
        }

    def action_open_hours_adjustment_wizard(self):
        self.ensure_one()
        self._check_editable()
        return {
            "type": "ir.actions.act_window",
            "name": _("Adjust Payable Hours"),
            "res_model": "spx.tt.payroll.hours.adjustment.wizard",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "spx_tt_payroll.view_tt_payroll_hours_adjustment_wizard_form"
                    ).id,
                    "form",
                )
            ],
            "target": "new",
            "context": {
                "default_run_employee_id": self.id,
            },
        }

    def action_open_hours_adjustments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payable Hours Adjustment History"),
            "res_model": "spx.tt.payroll.hours.adjustment",
            "view_mode": "list,form",
            "domain": [("run_employee_id", "=", self.id)],
            "context": {"create": False, "edit": False, "delete": False},
            "target": "current",
        }

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
            unresolved_exception = bool(
                line.incomplete_attendance_count
                or line.pending_overtime_hours
                or line.pending_time_off_count
                or line.time_off_attendance_overlap_hours
                or line.missing_hours
            )
            manual_adjustment_without_history = bool(
                line.attendance_adjustment_hours and not line.hours_adjustment_ids
            )
            if (unresolved_exception or manual_adjustment_without_history) and not line.attendance_review_note:
                raise UserError(
                    _(
                        "Enter an Attendance Review Note before confirming unresolved attendance exceptions. Manual adjustments made through Adjust Payable Hours already have their own reason history."
                    )
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

    def _payslip_visible_items(self, section):
        self.ensure_one()
        return self.item_line_ids.filtered(
            lambda item: item.show_on_payslip and item.payslip_section == section
        ).sorted(key=lambda item: (item.sequence, item.id))

    def _payslip_section_total(self, section):
        self.ensure_one()
        return sum(self._payslip_visible_items(section).mapped("amount"))

    def _payslip_summary_values(self):
        """Return the current and year-to-date values printed on the payslip.

        Only approved/paid historical payrolls are included. The current
        calculation is always included so a draft preview shows the expected
        YTD result without counting unrelated draft payrolls.
        """
        self.ensure_one()
        current = {
            "income": self._payslip_section_total("wage"),
            "additions": self._payslip_section_total("addition"),
            "gross": self.gross_pay,
            "paye": self.paye_amount,
            "hsur": self.health_surcharge_amount,
            "nis": self.employee_nis_amount,
            "deductions": self._payslip_section_total("deduction"),
            "loans": self._payslip_section_total("loan"),
            "net": self.net_pay,
        }
        payment_date = self.run_id.payment_date or self.run_id.date_end
        year = payment_date.year if payment_date else fields.Date.context_today(self).year
        profile = self._get_statutory_profile()
        ytd = {
            "income": profile.opening_income if profile and profile.opening_ytd_year == year else 0.0,
            "additions": profile.opening_additions if profile and profile.opening_ytd_year == year else 0.0,
            "gross": profile.opening_gross if profile and profile.opening_ytd_year == year else 0.0,
            "paye": profile.opening_paye if profile and profile.opening_ytd_year == year else 0.0,
            "hsur": profile.opening_health_surcharge if profile and profile.opening_ytd_year == year else 0.0,
            "nis": profile.opening_employee_nis if profile and profile.opening_ytd_year == year else 0.0,
            "deductions": profile.opening_other_deductions if profile and profile.opening_ytd_year == year else 0.0,
            "loans": profile.opening_loans if profile and profile.opening_ytd_year == year else 0.0,
            "net": profile.opening_net if profile and profile.opening_ytd_year == year else 0.0,
        }
        previous_domain = [
            ("employee_id", "=", self.employee_id.id),
            ("company_id", "=", self.company_id.id),
            ("id", "!=", self.id),
            ("run_id.state", "in", ["approved", "paid"]),
            ("review_state", "not in", ["on_hold", "excluded"]),
            ("run_id.payment_date", ">=", date(year, 1, 1)),
            ("run_id.payment_date", "<=", date(year, 12, 31)),
        ]
        if payment_date:
            previous_domain.append(("run_id.payment_date", "<=", payment_date))
        previous_lines = self.search(previous_domain)
        for previous in previous_lines:
            ytd["income"] += previous._payslip_section_total("wage")
            ytd["additions"] += previous._payslip_section_total("addition")
            ytd["gross"] += previous.gross_pay
            ytd["paye"] += previous.paye_amount
            ytd["hsur"] += previous.health_surcharge_amount
            ytd["nis"] += previous.employee_nis_amount
            ytd["deductions"] += previous._payslip_section_total("deduction")
            ytd["loans"] += previous._payslip_section_total("loan")
            ytd["net"] += previous.net_pay
        for key, value in current.items():
            ytd[key] += value
        return {"current": current, "ytd": ytd}

    def _masked_bank_account(self):
        self.ensure_one()
        account = (self.bank_account_number or "").strip()
        if not account:
            return ""
        visible = account[-4:]
        return ("*" * max(len(account) - 4, 4)) + visible

    def _selection_label(self, field_name, value, default=""):
        """Return a translated label for static, callable, or related selections."""
        self.ensure_one()
        if not value:
            return default
        field = self._fields[field_name]
        try:
            return dict(field._description_selection(self.env)).get(value, default or value)
        except (AttributeError, TypeError, ValueError):
            # Keep reports usable if a third-party module alters the field metadata.
            return default or value

    def _get_payslip_report_values(self):
        self.ensure_one()
        summary = self._payslip_summary_values()
        payment_label = self._selection_label(
            "payment_method", self.payment_method, _("Payment")
        )
        return {
            "wages": self._payslip_visible_items("wage"),
            "additions": self._payslip_visible_items("addition"),
            "taxes": self._payslip_visible_items("tax"),
            "deductions": self._payslip_visible_items("deduction"),
            "loans": self._payslip_visible_items("loan"),
            "wage_total": summary["current"]["income"],
            "addition_total": summary["current"]["additions"],
            "tax_total": sum(self._payslip_visible_items("tax").mapped("amount")),
            "deduction_total": summary["current"]["deductions"],
            "loan_total": summary["current"]["loans"],
            "summary": summary,
            "payment_label": payment_label,
            "status_label": self._selection_label(
                "run_state", self.run_state, self.run_state or ""
            ),
            "masked_account": self._masked_bank_account(),
            "is_draft": self.run_state not in ("approved", "paid"),
        }

    def action_preview_payslip(self):
        self.ensure_one()
        return self.env.ref(
            "spx_tt_payroll.action_report_tt_payroll_payslip_preview"
        ).report_action(self)

    def action_print_payslip(self):
        self.ensure_one()
        return self.env.ref(
            "spx_tt_payroll.action_report_tt_payroll_payslip_pdf"
        ).report_action(self)

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

    def action_open_time_off_snapshots(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payroll Time Off Snapshot"),
            "res_model": "spx.tt.payroll.time.off.snapshot",
            "view_mode": "list,form",
            "domain": [("run_employee_id", "=", self.id)],
            "context": {"create": False, "edit": False, "delete": False},
            "target": "current",
        }

    def action_open_time_off(self):
        self.ensure_one()
        return self.employee_id.action_tt_open_time_off(
            date_start=self.run_id.date_start,
            date_end=self.run_id.date_end,
        )

    def action_open_attendances(self):
        self.ensure_one()
        return self.employee_id.action_tt_open_attendances()

    def write(self, vals):
        if not self.env.context.get("tt_payroll_allow_locked_write"):
            editable_fields = set(vals) - {"message_follower_ids", "message_ids", "activity_ids"}
            if editable_fields:
                self._check_editable()
        if (
            "attendance_adjustment_hours" in vals
            and not self.env.context.get("tt_payroll_internal_write")
            and not self.env.context.get("tt_payroll_hours_wizard")
        ):
            raise UserError(
                _(
                    "Use the Adjust Payable Hours button. A reason is required for every manual hours change."
                )
            )
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
