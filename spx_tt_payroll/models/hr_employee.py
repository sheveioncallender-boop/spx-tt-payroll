from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HREmployee(models.Model):
    _inherit = "hr.employee"

    tt_payroll_enabled = fields.Boolean(
        string="Payroll Active (Legacy)",
        default=True,
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_status = fields.Selection(
        [
            ("active", "Active"),
            ("on_hold", "On Hold"),
            ("excluded", "Excluded"),
        ],
        default="active",
        required=True,
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_pay_type = fields.Selection(
        [
            ("monthly", "Monthly Salary"),
            ("weekly", "Weekly Salary"),
            ("daily", "Daily Paid"),
            ("hourly", "Hourly Paid"),
        ],
        string="Pay Basis",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_pay_frequency_id = fields.Many2one(
        "spx.tt.pay.frequency",
        string="Pay Frequency",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_group_id = fields.Many2one(
        "spx.tt.payroll.group",
        string="Payroll Group",
        check_company=True,
        domain="[('company_id', '=', company_id)]",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_monthly_salary = fields.Monetary(
        string="Monthly Salary",
        currency_field="tt_currency_id",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_weekly_salary = fields.Monetary(
        string="Weekly Salary",
        currency_field="tt_currency_id",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_daily_rate = fields.Monetary(
        string="Daily Rate",
        currency_field="tt_currency_id",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_hourly_rate = fields.Monetary(
        string="Hourly Rate",
        currency_field="tt_currency_id",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_normal_hours_per_day = fields.Float(
        string="Normal Hours per Day",
        default=8.0,
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_normal_hours_per_week = fields.Float(
        string="Normal Hours per Week",
        default=40.0,
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_bir_number = fields.Char(
        string="BIR Number",
        copy=False,
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_nis_number = fields.Char(
        string="NIS Number",
        copy=False,
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_nis_exempt = fields.Boolean(
        string="NIS Exempt",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_health_surcharge_exempt = fields.Boolean(
        string="Health Surcharge Exempt",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_statutory_exemption_reason = fields.Char(
        string="Exemption Reason",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payment_method = fields.Selection(
        [
            ("bank", "Bank Transfer"),
            ("cash", "Cash"),
            ("cheque", "Cheque"),
        ],
        default="bank",
        required=True,
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_bank_name = fields.Char(
        string="Bank",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_bank_branch = fields.Char(
        string="Branch",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_bank_account_name = fields.Char(
        string="Account Name",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_bank_account_number = fields.Char(
        string="Account Number",
        copy=False,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_bank_account_type = fields.Selection(
        [
            ("savings", "Savings"),
            ("chequing", "Chequing"),
            ("other", "Other"),
        ],
        string="Account Type",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_start_date = fields.Date(
        string="Payroll Start Date",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_end_date = fields.Date(
        string="Payroll End Date",
        tracking=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_recurring_pay_item_ids = fields.One2many(
        "spx.tt.employee.pay.item",
        "employee_id",
        string="Recurring Earnings and Deductions",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_readiness_state = fields.Selection(
        [
            ("not_enrolled", "Excluded"),
            ("incomplete", "Needs Setup"),
            ("ready", "Ready"),
        ],
        compute="_compute_tt_payroll_readiness",
        store=True,
        string="Payroll Readiness",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_issue_count = fields.Integer(
        compute="_compute_tt_payroll_readiness",
        store=True,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_issue_summary = fields.Text(
        compute="_compute_tt_payroll_readiness",
        store=True,
        string="Items to Complete",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )


    @api.model_create_multi
    def create(self, vals_list):
        """Apply editable company payroll defaults only after installation.

        Field-level defaults must not read custom ``res.company`` columns while
        Odoo is creating the database schema. Doing so can fail on a fresh
        install because the company columns may not exist yet.
        """
        prepared_vals = []
        Company = self.env["res.company"]
        for incoming in vals_list:
            vals = dict(incoming)
            company = (
                Company.browse(vals["company_id"])
                if vals.get("company_id")
                else self.env.company
            )
            if not vals.get("tt_pay_frequency_id"):
                vals["tt_pay_frequency_id"] = (
                    company.tt_payroll_default_frequency_id.id or False
                )
            if not vals.get("tt_normal_hours_per_day"):
                vals["tt_normal_hours_per_day"] = (
                    company.tt_payroll_default_hours_per_day or 8.0
                )
            if not vals.get("tt_normal_hours_per_week"):
                vals["tt_normal_hours_per_week"] = (
                    company.tt_payroll_default_hours_per_week or 40.0
                )
            prepared_vals.append(vals)
        return super().create(prepared_vals)

    @api.onchange("company_id", "tt_payroll_status")
    def _onchange_tt_payroll_defaults(self):
        """Suggest company defaults on the normal Odoo employee record."""
        if self.tt_payroll_status == "excluded":
            return
        company = self.company_id or self.env.company
        if not self.tt_pay_frequency_id:
            self.tt_pay_frequency_id = company.tt_payroll_default_frequency_id
        if not self.tt_normal_hours_per_day:
            self.tt_normal_hours_per_day = (
                company.tt_payroll_default_hours_per_day or 8.0
            )
        if not self.tt_normal_hours_per_week:
            self.tt_normal_hours_per_week = (
                company.tt_payroll_default_hours_per_week or 40.0
            )

    @api.onchange("tt_payroll_group_id")
    def _onchange_tt_payroll_group_id(self):
        if self.tt_payroll_group_id:
            self.tt_pay_frequency_id = self.tt_payroll_group_id.pay_frequency_id
            self.tt_normal_hours_per_day = (
                self.tt_payroll_group_id.normal_hours_per_day
            )
            self.tt_normal_hours_per_week = (
                self.tt_payroll_group_id.normal_hours_per_week
            )

    @api.onchange("tt_nis_exempt", "tt_health_surcharge_exempt")
    def _onchange_tt_exemptions(self):
        if not self.tt_nis_exempt and not self.tt_health_surcharge_exempt:
            self.tt_statutory_exemption_reason = False

    def _tt_get_payroll_issues(self):
        self.ensure_one()
        if self.tt_payroll_status == "excluded":
            return []

        issues = []
        if not self.tt_pay_frequency_id:
            issues.append("Select a pay frequency")
        if not self.tt_pay_type:
            issues.append("Select how the employee is paid")
        elif self.tt_pay_type == "monthly" and self.tt_monthly_salary <= 0:
            issues.append("Enter the monthly salary")
        elif self.tt_pay_type == "weekly" and self.tt_weekly_salary <= 0:
            issues.append("Enter the weekly salary")
        elif self.tt_pay_type == "daily" and self.tt_daily_rate <= 0:
            issues.append("Enter the daily rate")
        elif self.tt_pay_type == "hourly" and self.tt_hourly_rate <= 0:
            issues.append("Enter the hourly rate")
        if not self.resource_calendar_id:
            issues.append("Assign a work schedule")
        if not self.tt_bir_number:
            issues.append("Enter the BIR number")
        if not self.tt_nis_exempt and not self.tt_nis_number:
            issues.append("Enter the NIS number or mark the employee as exempt")
        if self.tt_payment_method == "bank":
            if not self.tt_bank_name:
                issues.append("Enter the employee's bank")
            if not self.tt_bank_account_number:
                issues.append("Enter the bank account number")
        if self.tt_normal_hours_per_day <= 0:
            issues.append("Enter normal hours per day")
        if self.tt_normal_hours_per_week <= 0:
            issues.append("Enter normal hours per week")
        return issues

    @api.depends(
        "tt_payroll_status",
        "tt_pay_frequency_id",
        "tt_pay_type",
        "tt_monthly_salary",
        "tt_weekly_salary",
        "tt_daily_rate",
        "tt_hourly_rate",
        "resource_calendar_id",
        "tt_bir_number",
        "tt_nis_number",
        "tt_nis_exempt",
        "tt_payment_method",
        "tt_bank_name",
        "tt_bank_account_number",
        "tt_normal_hours_per_day",
        "tt_normal_hours_per_week",
    )
    def _compute_tt_payroll_readiness(self):
        for employee in self:
            if employee.tt_payroll_status == "excluded":
                employee.tt_payroll_readiness_state = "not_enrolled"
                employee.tt_payroll_issue_count = 0
                employee.tt_payroll_issue_summary = False
                continue
            issues = employee._tt_get_payroll_issues()
            employee.tt_payroll_issue_count = len(issues)
            employee.tt_payroll_readiness_state = (
                "incomplete" if issues else "ready"
            )
            employee.tt_payroll_issue_summary = (
                "\n".join(f"• {issue}" for issue in issues)
                if issues
                else "Payroll information is complete."
            )

    def action_tt_open_attendances(self):
        """Open this employee's records in Odoo Attendances.

        Payroll never creates a second attendance database. Phase 2 will read
        and validate these standard ``hr.attendance`` records directly.
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_attendance.hr_attendance_action"
        )
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {"default_employee_id": self.id}
        return action

    @api.constrains(
        "tt_monthly_salary",
        "tt_weekly_salary",
        "tt_daily_rate",
        "tt_hourly_rate",
        "tt_normal_hours_per_day",
        "tt_normal_hours_per_week",
    )
    def _check_tt_payroll_numbers(self):
        for employee in self:
            values = [
                employee.tt_monthly_salary,
                employee.tt_weekly_salary,
                employee.tt_daily_rate,
                employee.tt_hourly_rate,
                employee.tt_normal_hours_per_day,
                employee.tt_normal_hours_per_week,
            ]
            if any(value < 0 for value in values):
                raise ValidationError("Payroll rates and hours cannot be negative.")

    @api.constrains("tt_payroll_start_date", "tt_payroll_end_date")
    def _check_tt_payroll_dates(self):
        for employee in self:
            if (
                employee.tt_payroll_start_date
                and employee.tt_payroll_end_date
                and employee.tt_payroll_end_date < employee.tt_payroll_start_date
            ):
                raise ValidationError(
                    "The payroll end date cannot be before the payroll start date."
                )
