from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class TTPayrollRun(models.Model):
    _name = "spx.tt.payroll.run"
    _description = "Trinidad Payroll Run"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "payment_date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_period_start(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    @api.model
    def _default_period_end(self):
        start = self._default_period_start()
        return start + relativedelta(months=1, days=-1)

    name = fields.Char(
        string="Payroll Run",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    pay_frequency_id = fields.Many2one(
        "spx.tt.pay.frequency",
        string="Pay Frequency",
        required=True,
        default=lambda self: self.env.company.tt_payroll_default_frequency_id,
        tracking=True,
    )
    payroll_group_id = fields.Many2one(
        "spx.tt.payroll.group",
        string="Payroll Group",
        check_company=True,
        domain="[('company_id', '=', company_id)]",
        tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    date_start = fields.Date(
        string="Period Start",
        required=True,
        default=_default_period_start,
        tracking=True,
    )
    date_end = fields.Date(
        string="Period End",
        required=True,
        default=_default_period_end,
        tracking=True,
    )
    payment_date = fields.Date(
        string="Pay Date",
        required=True,
        default=_default_period_end,
        tracking=True,
    )
    payroll_year = fields.Integer(
        string="Payroll Year",
        compute="_compute_period_information",
        store=True,
    )
    period_day_count = fields.Integer(
        string="Calendar Days",
        compute="_compute_period_information",
        store=True,
    )
    monday_count = fields.Integer(
        string="Mondays",
        compute="_compute_period_information",
        store=True,
        help="Number of Mondays falling inside this payroll period.",
    )
    period_week_count = fields.Integer(
        string="Payroll Weeks",
        compute="_compute_period_information",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("attendance_review", "Attendance Review"),
            ("calculated", "Calculated"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    employee_line_ids = fields.One2many(
        "spx.tt.payroll.run.employee",
        "run_id",
        string="Employees",
        copy=False,
    )
    employee_count = fields.Integer(
        compute="_compute_run_totals",
        store=True,
    )
    payable_employee_count = fields.Integer(
        string="Employees Payable",
        compute="_compute_run_totals",
        store=True,
    )
    needs_attention_count = fields.Integer(
        string="Needs Attention",
        compute="_compute_run_totals",
        store=True,
    )
    reviewed_count = fields.Integer(
        string="Reviewed",
        compute="_compute_run_totals",
        store=True,
    )
    held_count = fields.Integer(
        string="On Hold",
        compute="_compute_run_totals",
        store=True,
    )
    gross_pay = fields.Monetary(
        string="Gross Pay",
        currency_field="currency_id",
        compute="_compute_run_totals",
        store=True,
    )
    total_deductions = fields.Monetary(
        string="Total Deductions",
        currency_field="currency_id",
        compute="_compute_run_totals",
        store=True,
    )
    employer_contributions = fields.Monetary(
        string="Employer Contributions",
        currency_field="currency_id",
        compute="_compute_run_totals",
        store=True,
    )
    net_pay = fields.Monetary(
        string="Net Pay",
        currency_field="currency_id",
        compute="_compute_run_totals",
        store=True,
    )
    notes = fields.Text()

    @api.depends("date_start", "date_end", "payment_date")
    def _compute_period_information(self):
        for run in self:
            run.payroll_year = (run.payment_date or run.date_end or fields.Date.context_today(run)).year
            if not run.date_start or not run.date_end or run.date_end < run.date_start:
                run.period_day_count = 0
                run.monday_count = 0
                run.period_week_count = 0
                continue

            day_count = (run.date_end - run.date_start).days + 1
            run.period_day_count = day_count
            run.period_week_count = max(1, (day_count + 6) // 7)

            current = run.date_start
            monday_count = 0
            while current <= run.date_end:
                if current.weekday() == 0:
                    monday_count += 1
                current += relativedelta(days=1)
            run.monday_count = monday_count

    @api.depends(
        "employee_line_ids.gross_pay",
        "employee_line_ids.total_deductions",
        "employee_line_ids.employer_contribution_total",
        "employee_line_ids.net_pay",
        "employee_line_ids.review_state",
        "employee_line_ids.display_status",
    )
    def _compute_run_totals(self):
        for run in self:
            lines = run.employee_line_ids
            payable_lines = lines.filtered(
                lambda line: line.review_state not in ("on_hold", "excluded")
            )
            run.employee_count = len(lines)
            run.payable_employee_count = len(payable_lines)
            run.needs_attention_count = len(
                lines.filtered(lambda line: line.display_status == "needs_attention")
            )
            run.reviewed_count = len(
                lines.filtered(lambda line: line.display_status == "reviewed")
            )
            run.held_count = len(
                lines.filtered(lambda line: line.review_state == "on_hold")
            )
            run.gross_pay = sum(payable_lines.mapped("gross_pay"))
            run.total_deductions = sum(payable_lines.mapped("total_deductions"))
            run.employer_contributions = sum(
                payable_lines.mapped("employer_contribution_total")
            )
            run.net_pay = sum(payable_lines.mapped("net_pay"))

    @api.onchange("payroll_group_id")
    def _onchange_payroll_group_id(self):
        if self.payroll_group_id:
            self.pay_frequency_id = self.payroll_group_id.pay_frequency_id

    @api.onchange("pay_frequency_id", "date_start")
    def _onchange_period_from_frequency(self):
        if not self.pay_frequency_id or not self.date_start or self.employee_line_ids:
            return
        code = self.pay_frequency_id.code
        if code == "WEEKLY":
            suggested_end = self.date_start + relativedelta(days=6)
        elif code == "FORTNIGHTLY":
            suggested_end = self.date_start + relativedelta(days=13)
        elif code == "SEMI_MONTHLY":
            if self.date_start.day <= 15:
                suggested_end = self.date_start.replace(day=15)
            else:
                suggested_end = self.date_start + relativedelta(months=1, day=1, days=-1)
        elif code == "MONTHLY":
            suggested_end = self.date_start + relativedelta(months=1, day=1, days=-1)
        else:
            return
        self.date_end = suggested_end
        self.payment_date = suggested_end

    @api.constrains("date_start", "date_end")
    def _check_period_dates(self):
        for run in self:
            if run.date_start and run.date_end and run.date_end < run.date_start:
                raise ValidationError(_("The period end date cannot be before the start date."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("spx.tt.payroll.run")
                    or _("New")
                )
        runs = super().create(vals_list)
        # A normal payroll run should be ready for review as soon as it is saved.
        # Employees are loaded silently here; the Generate Payroll button remains
        # available to add any employees who become eligible afterwards.
        if not self.env.context.get("skip_tt_payroll_auto_load"):
            for run in runs:
                run._load_eligible_employees(silent=True, change_state=False)
        return runs

    def write(self, vals):
        protected_setup_fields = {
            "company_id",
            "pay_frequency_id",
            "payroll_group_id",
            "department_id",
            "date_start",
            "date_end",
        }
        if protected_setup_fields.intersection(vals):
            for run in self:
                if run.employee_line_ids:
                    raise UserError(
                        _(
                            "Clear the employees from this draft payroll before changing "
                            "the company, period, frequency, payroll group, or department."
                        )
                    )
        return super().write(vals)

    def _check_state(self, allowed_states):
        for run in self:
            if run.state not in allowed_states:
                raise UserError(
                    _("This action is not available while the payroll is in %s.")
                    % dict(self._fields["state"].selection).get(run.state)
                )

    def _eligible_employee_domain(self):
        self.ensure_one()
        domain = [
            ("active", "=", True),
            ("company_id", "=", self.company_id.id),
            ("tt_payroll_status", "in", ["active", "on_hold"]),
        ]
        if self.payroll_group_id:
            domain.append(("tt_payroll_group_id", "=", self.payroll_group_id.id))
        elif self.pay_frequency_id and self.pay_frequency_id.code != "OFF_CYCLE":
            domain.append(("tt_pay_frequency_id", "=", self.pay_frequency_id.id))
        if self.department_id:
            domain.append(("department_id", "=", self.department_id.id))
        existing_employee_ids = self.employee_line_ids.employee_id.ids
        if existing_employee_ids:
            domain.append(("id", "not in", existing_employee_ids))
        return domain

    def _load_eligible_employees(self, silent=False, change_state=True):
        self.ensure_one()
        if not self.pay_frequency_id:
            if silent:
                return self.env["spx.tt.payroll.run.employee"]
            raise UserError(_("Select a pay frequency before loading employees."))
        employees = self.env["hr.employee"].search(
            self._eligible_employee_domain(), order="department_id, name"
        )
        if not employees:
            return self.env["spx.tt.payroll.run.employee"]
        created_lines = self.env["spx.tt.payroll.run.employee"].create(
            [{"run_id": self.id, "employee_id": employee.id} for employee in employees]
        )
        if change_state:
            self.state = "attendance_review"
        if not silent:
            self.message_post(
                body=_(
                    "%s employee(s) were added. Odoo attendance was pulled and the automatic earnings, recurring items, and statutory lines were generated."
                ) % len(created_lines)
            )
        return created_lines

    def action_load_employees(self):
        self.ensure_one()
        self._check_state({"draft", "attendance_review"})
        created_lines = self._load_eligible_employees(silent=False, change_state=True)
        if not created_lines:
            message = _("No additional eligible employees were found for this payroll run.")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {"title": _("Payroll Employees"), "message": message, "type": "warning"},
            }
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_refresh_attendance(self):
        self.ensure_one()
        self._check_state({"draft", "attendance_review", "calculated"})
        if not self.employee_line_ids:
            raise UserError(_("Generate the payroll before refreshing attendance."))
        self.employee_line_ids.action_refresh_attendance()
        self.state = "attendance_review"
        self.message_post(body=_("Attendance and automatic attendance-based earnings were refreshed."))
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_clear_employees(self):
        self.ensure_one()
        self._check_state({"draft", "attendance_review"})
        self.employee_line_ids.unlink()
        self.state = "draft"
        return True

    def action_open_employee_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_run_employees"
        )
        action["name"] = _("%s - Employee Calculations") % self.name
        action["domain"] = [("run_id", "=", self.id)]
        action["context"] = {"default_run_id": self.id}
        return action

    def action_start_attendance_review(self):
        self._check_state({"draft"})
        for run in self:
            if not run.employee_line_ids:
                raise UserError(_("Load employees before starting attendance review."))
            run.state = "attendance_review"
        return True

    def action_calculate(self):
        self._check_state({"draft", "attendance_review", "calculated"})
        for run in self:
            if not run.employee_line_ids:
                raise UserError(_("Generate the payroll before calculating."))
            run.employee_line_ids._recalculate_payable_hours()
            run.employee_line_ids._rebuild_attendance_earnings()
            run.state = "calculated"
        return True

    def action_submit_for_review(self):
        self._check_state({"calculated"})
        for run in self:
            run.state = "under_review"
        return True

    def action_approve(self):
        self._check_state({"under_review", "calculated"})
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can approve payroll."))
        for run in self:
            problem_lines = run.employee_line_ids.filtered(
                lambda line: line.review_state not in ("on_hold", "excluded")
                and line.display_status == "needs_attention"
            )
            if problem_lines:
                raise UserError(
                    _(
                        "%s employee(s) still need attention. Correct them, place them on hold, "
                        "or exclude them from this run before approval."
                    )
                    % len(problem_lines)
                )
            if run.company_id.tt_payroll_require_review:
                unreviewed_lines = run.employee_line_ids.filtered(
                    lambda line: line.review_state not in ("on_hold", "excluded", "reviewed")
                )
                if unreviewed_lines:
                    raise UserError(
                        _(
                            "%s payable employee(s) have not been marked Reviewed."
                        )
                        % len(unreviewed_lines)
                    )
            run.state = "approved"
        return True

    def action_mark_paid(self):
        self._check_state({"approved"})
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can mark payroll as paid."))
        self.write({"state": "paid"})
        return True

    def action_reset_to_draft(self):
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can reset payroll to draft."))
        self.write({"state": "draft"})
        return True

    def action_cancel(self):
        if not self.env.user.has_group("spx_tt_payroll.group_tt_payroll_manager"):
            raise UserError(_("Only a Payroll Manager can cancel payroll."))
        self.write({"state": "cancelled"})
        return True

    def unlink(self):
        protected = self.filtered(lambda run: run.state not in ("draft", "cancelled"))
        if protected:
            raise UserError(_("Only draft or cancelled payroll runs can be deleted."))
        return super().unlink()
