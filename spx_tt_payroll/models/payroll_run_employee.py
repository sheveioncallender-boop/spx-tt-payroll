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
    pay_type = fields.Selection(
        [
            ("monthly", "Monthly Salary"),
            ("weekly", "Weekly Salary"),
            ("daily", "Daily Paid"),
            ("hourly", "Hourly Paid"),
        ],
        string="Pay Basis",
    )
    base_rate = fields.Monetary(string="Base Rate", currency_field="currency_id")
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

    scheduled_days = fields.Float(string="Scheduled Days")
    scheduled_hours = fields.Float(string="Scheduled Hours")
    regular_hours = fields.Float(string="Regular Hours")
    overtime_hours = fields.Float(string="Overtime Hours")
    public_holiday_hours = fields.Float(string="Public Holiday Hours")
    paid_leave_hours = fields.Float(string="Paid Leave Hours")
    unpaid_hours = fields.Float(string="Unpaid Hours")
    attendance_status = fields.Selection(
        [
            ("not_loaded", "Not Loaded"),
            ("needs_attention", "Needs Attention"),
            ("ready", "Ready"),
        ],
        default="not_loaded",
        string="Attendance Status",
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
    def _employee_snapshot_values(self, employee, run):
        pay_map = {
            "monthly": (employee.tt_monthly_salary, "Month"),
            "weekly": (employee.tt_weekly_salary, "Week"),
            "daily": (employee.tt_daily_rate, "Day"),
            "hourly": (employee.tt_hourly_rate, "Hour"),
        }
        base_rate, pay_unit = pay_map.get(employee.tt_pay_type, (0.0, ""))
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
        "pay_type",
        "pay_frequency_id",
        "base_rate",
        "payment_method",
        "bank_name",
        "bank_account_number",
        "bir_number",
        "nis_number",
        "nis_exempt",
        "gross_pay",
        "net_pay",
        "item_line_ids.amount",
        "item_line_ids.quantity",
        "item_line_ids.source",
        "item_line_ids.category",
        "review_state",
    )
    def _compute_issues_and_status(self):
        for line in self:
            issues = []
            if not line.pay_type:
                issues.append(_("Pay basis is missing."))
            if not line.pay_frequency_id:
                issues.append(_("Pay frequency is missing."))
            if line.base_rate <= 0:
                issues.append(_("Base pay or rate is missing."))
            if not line.bir_number:
                issues.append(_("BIR number is missing."))
            if not line.nis_exempt and not line.nis_number:
                issues.append(_("NIS number is missing."))
            if line.payment_method == "bank":
                if not line.bank_name:
                    issues.append(_("Bank name is missing."))
                if not line.bank_account_number:
                    issues.append(_("Bank account number is missing."))
            if not line.item_line_ids.filtered(lambda item: item.category == "earning"):
                issues.append(_("No earnings have been added."))
            if line.pay_type in ("daily", "hourly"):
                basic_line = line.item_line_ids.filtered(
                    lambda item: item.source == "basic"
                )[:1]
                if basic_line and basic_line.quantity <= 0:
                    unit_label = _("days") if line.pay_type == "daily" else _("hours")
                    issues.append(_("Enter the payable %s on the Basic Pay line.") % unit_label)
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

    def _basic_quantity(self):
        self.ensure_one()
        if self.pay_type == "monthly":
            return 1.0
        if self.pay_type == "weekly":
            return float(self.run_id.period_week_count or 1)
        return 0.0

    def _prepare_basic_item_values(self):
        self.ensure_one()
        pay_item = self.env.ref("spx_tt_payroll.pay_item_basic")
        return {
            "run_employee_id": self.id,
            "pay_item_id": pay_item.id,
            "description": dict(self._fields["pay_type"].selection).get(self.pay_type)
            or pay_item.name,
            "category": "earning",
            "calculation_method": "fixed",
            "rate": self.base_rate,
            "quantity": self._basic_quantity(),
            "factor": 1.0,
            "source": "basic",
            "taxable": True,
            "nis_applicable": True,
            "show_on_payslip": True,
            "sequence": 10,
        }

    def _prepare_recurring_item_values(self, recurring_item, basic_amount):
        pay_item = recurring_item.pay_item_id
        values = {
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
            "base_amount": basic_amount,
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
        return values

    def _load_default_items(self):
        item_model = self.env["spx.tt.payroll.run.item"]
        values_list = []
        for line in self:
            basic_line = line.item_line_ids.filtered(
                lambda item: item.source == "basic"
            )[:1]
            if basic_line:
                basic_amount = basic_line.amount
            else:
                basic_values = line._prepare_basic_item_values()
                values_list.append(basic_values)
                basic_amount = basic_values["rate"] * basic_values["quantity"]

            recurring_items = line.employee_id.tt_recurring_pay_item_ids.filtered(
                lambda item: item.active
                and (not item.start_date or item.start_date <= line.run_id.date_end)
                and (not item.end_date or item.end_date >= line.run_id.date_start)
            )
            existing_recurring_keys = {
                item.employee_pay_item_id.id
                for item in line.item_line_ids.filtered(
                    lambda payroll_item: payroll_item.source == "recurring"
                    and payroll_item.employee_pay_item_id
                )
            }
            for recurring_item in recurring_items:
                key = recurring_item.id
                if key in existing_recurring_keys:
                    continue
                values_list.append(
                    line._prepare_recurring_item_values(recurring_item, basic_amount)
                )
        if values_list:
            item_model.create(values_list)

    def _ensure_basic_pay_line(self):
        for line in self:
            if not line.item_line_ids.filtered(lambda item: item.source == "basic"):
                self.env["spx.tt.payroll.run.item"].create(
                    line._prepare_basic_item_values()
                )
        return True

    def _check_editable(self):
        for line in self:
            if line.run_state in ("approved", "paid", "cancelled"):
                raise UserError(_("Approved, paid, or cancelled payroll calculations are locked."))

    def action_refresh_from_employee(self):
        self._check_editable()
        for line in self:
            snapshot = line._employee_snapshot_values(line.employee_id, line.run_id)
            line.write(snapshot)
            auto_items = line.item_line_ids.filtered(
                lambda item: item.source in ("basic", "recurring")
            )
            auto_items.unlink()
            line._load_default_items()
        return True

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
        return self.employee_id.action_open_tt_attendances()

    def write(self, vals):
        if not self.env.context.get("tt_payroll_allow_locked_write"):
            editable_fields = set(vals) - {"message_follower_ids", "message_ids", "activity_ids"}
            if editable_fields:
                self._check_editable()
        return super().write(vals)

    def unlink(self):
        self._check_editable()
        return super().unlink()
