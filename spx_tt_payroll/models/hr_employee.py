from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HREmployee(models.Model):
    _inherit = "hr.employee"

    # Core Phase 1 payroll fields. These columns already existed in v1.0.6.
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
        string="Payroll Status",
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
    # Simple payroll-facing aliases. These are intentionally non-stored so
    # upgrading the module cannot put hr.employee ahead of its database table.
    # The legacy tt_pay_type column remains for backward compatibility.
    tt_pay_basis = fields.Selection(
        [("salary", "Salaried"), ("hourly", "Hourly Paid")],
        string="Pay Basis",
        compute="_compute_tt_pay_basis",
        inverse="_inverse_tt_pay_basis",
        search="_search_tt_pay_basis",
        store=False,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_salary = fields.Monetary(
        string="Salary",
        currency_field="tt_currency_id",
        compute="_compute_tt_salary",
        inverse="_inverse_tt_salary",
        store=False,
        groups="spx_tt_payroll.group_tt_payroll_user",
        help="The employee's normal monthly salary. The payroll run converts it to the selected pay frequency and prorates it from approved payable hours.",
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
        string="Payment Method",
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
    tt_recurring_pay_item_ids = fields.One2many(
        "spx.tt.employee.pay.item",
        "employee_id",
        string="Recurring Earnings and Deductions",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )

    # Non-stored helper fields used by the modern workspace. They deliberately
    # do not add columns to hr_employee, making code deployment safe before the
    # module upgrade is executed.
    tt_current_pay_amount = fields.Monetary(
        string="Current Base Pay",
        currency_field="tt_currency_id",
        compute="_compute_tt_current_pay",
        store=False,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_current_pay_unit = fields.Char(
        string="Pay Unit",
        compute="_compute_tt_current_pay",
        store=False,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_recurring_earning_ids = fields.One2many(
        "spx.tt.employee.pay.item",
        "employee_id",
        string="Recurring Earnings",
        domain=[("category", "=", "earning")],
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_recurring_deduction_ids = fields.One2many(
        "spx.tt.employee.pay.item",
        "employee_id",
        string="Recurring Deductions",
        domain=[("category", "=", "deduction")],
        groups="spx_tt_payroll.group_tt_payroll_user",
    )

    # Compatibility aliases for the interrupted v1.1.0 deployment. These are
    # non-stored, so Odoo never expects missing database columns.
    tt_employee_number = fields.Char(
        string="Employee / Clock ID",
        related="barcode",
        readonly=False,
        store=False,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payment_currency_id = fields.Many2one(
        "res.currency",
        string="Payment Currency",
        related="company_id.currency_id",
        readonly=True,
        store=False,
        groups="spx_tt_payroll.group_tt_payroll_user",
    )

    tt_payroll_readiness_state = fields.Selection(
        [
            ("not_enrolled", "Excluded"),
            ("incomplete", "Needs Attention"),
            ("ready", "Complete"),
        ],
        compute="_compute_tt_payroll_readiness",
        search="_search_tt_payroll_readiness_state",
        store=False,
        string="Setup Status",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_issue_count = fields.Integer(
        compute="_compute_tt_payroll_readiness",
        store=False,
        string="Items to Complete",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )
    tt_payroll_issue_summary = fields.Text(
        compute="_compute_tt_payroll_readiness",
        store=False,
        string="Items to Complete",
        groups="spx_tt_payroll.group_tt_payroll_user",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Apply editable company defaults after the module is installed."""
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

    @api.depends("tt_pay_type")
    def _compute_tt_pay_basis(self):
        for employee in self:
            employee.tt_pay_basis = (
                "hourly" if employee.tt_pay_type in ("hourly", "daily") else "salary"
            ) if employee.tt_pay_type else False

    def _inverse_tt_pay_basis(self):
        for employee in self:
            employee.tt_pay_type = (
                "hourly" if employee.tt_pay_basis == "hourly" else "monthly"
            ) if employee.tt_pay_basis else False

    @api.model
    def _search_tt_pay_basis(self, operator, value):
        if operator not in ("=", "!=", "in", "not in"):
            raise ValidationError(
                "Pay Basis only supports equals, not equals, in, and not in filters."
            )
        values = value if operator in ("in", "not in") else [value]
        mapped = set()
        for item in values:
            if item == "salary":
                mapped.update(("monthly", "weekly"))
            elif item == "hourly":
                mapped.update(("hourly", "daily"))
            elif not item:
                mapped.add(False)
        if operator in ("=", "in"):
            return [("tt_pay_type", "in", list(mapped))]
        return [("tt_pay_type", "not in", list(mapped))]

    @api.depends("tt_monthly_salary")
    def _compute_tt_salary(self):
        for employee in self:
            employee.tt_salary = employee.tt_monthly_salary

    def _inverse_tt_salary(self):
        for employee in self:
            employee.tt_monthly_salary = employee.tt_salary

    @api.depends(
        "tt_pay_type",
        "tt_monthly_salary",
        "tt_hourly_rate",
    )
    def _compute_tt_current_pay(self):
        for employee in self:
            if employee.tt_pay_basis == "salary":
                employee.tt_current_pay_amount = employee.tt_monthly_salary
                employee.tt_current_pay_unit = "monthly salary"
            elif employee.tt_pay_basis == "hourly":
                employee.tt_current_pay_amount = employee.tt_hourly_rate
                employee.tt_current_pay_unit = "per hour"
            else:
                employee.tt_current_pay_amount = 0.0
                employee.tt_current_pay_unit = False

    def _tt_get_payroll_issues(self):
        self.ensure_one()
        if self.tt_payroll_status == "excluded":
            return []

        issues = []
        if not self.tt_pay_frequency_id:
            issues.append("Select a pay frequency")
        if not self.tt_pay_basis:
            issues.append("Select the pay basis")
        elif self.tt_pay_basis == "salary" and self.tt_monthly_salary <= 0:
            issues.append("Enter the salary")
        elif self.tt_pay_basis == "hourly" and self.tt_hourly_rate <= 0:
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
                else "Payroll setup is complete."
            )

    @api.model
    def _search_tt_payroll_readiness_state(self, operator, value):
        """Search the live setup state without relying on stale stored values."""
        if operator not in ("=", "!=", "in", "not in"):
            raise ValidationError(
                "Setup Status only supports equals, not equals, in, and not in filters."
            )

        wanted = value if operator in ("in", "not in") else [value]
        wanted = set(wanted)
        employees = self.search([])

        def current_state(employee):
            if employee.tt_payroll_status == "excluded":
                return "not_enrolled"
            return "incomplete" if employee._tt_get_payroll_issues() else "ready"

        matching_ids = employees.filtered(
            lambda employee: current_state(employee) in wanted
        ).ids
        if operator in ("=", "in"):
            return [("id", "in", matching_ids)]
        return [("id", "not in", matching_ids)]

    def action_tt_open_attendances(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_attendance.hr_attendance_action"
        )
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {"default_employee_id": self.id}
        return action

    def action_tt_open_time_off(self, date_start=None, date_end=None):
        self.ensure_one()
        domain = [("employee_id", "=", self.id)]
        if date_start:
            domain.append(("date_to", ">=", fields.Datetime.to_datetime(date_start)))
        if date_end:
            end_exclusive = fields.Datetime.to_datetime(date_end) + timedelta(days=1)
            domain.append(("date_from", "<", end_exclusive))
        return {
            "type": "ir.actions.act_window",
            "name": _("Employee Time Off"),
            "res_model": "hr.leave",
            "view_mode": "list,calendar,form",
            "domain": domain,
            "context": {"default_employee_id": self.id},
            "target": "current",
        }

    def action_open_tt_attendances(self):
        """Backward-compatible alias for earlier payroll workspace calls."""
        return self.action_tt_open_attendances()

    def action_tt_open_payroll_profile(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "TT Payroll Employee",
            "res_model": "hr.employee",
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "spx_tt_payroll.view_tt_payroll_employee_form"
                    ).id,
                    "form",
                )
            ],
            "target": "current",
        }

    def action_tt_open_statutory_profile(self):
        self.ensure_one()
        Profile = self.env["spx.tt.employee.statutory.profile"]
        profile = Profile.search([("employee_id", "=", self.id)], limit=1)
        if not profile:
            profile = Profile.create({"employee_id": self.id})
        action = self.env.ref(
            "spx_tt_payroll.action_tt_employee_statutory_profile"
        ).read()[0]
        action["res_id"] = profile.id
        action["context"] = {"default_employee_id": self.id}
        return action

    def action_tt_open_full_employee_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Employee",
            "res_model": "hr.employee",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(self.env.ref("hr.view_employee_form").id, "form")],
            "target": "current",
        }

    @api.constrains(
        "tt_monthly_salary",
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
