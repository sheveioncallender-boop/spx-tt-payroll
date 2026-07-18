from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
from markupsafe import Markup, escape


class TTPayrollDashboard(models.TransientModel):
    _name = "spx.tt.payroll.dashboard"
    _description = "Trinidad Payroll Dashboard"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name")

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    payroll_run_id = fields.Many2one(
        "spx.tt.payroll.run",
        string="Current Payroll",
        readonly=True,
    )
    has_current_run = fields.Boolean(compute="_compute_dashboard")
    run_name = fields.Char(compute="_compute_dashboard")
    run_period = fields.Char(compute="_compute_dashboard")
    run_pay_date = fields.Date(compute="_compute_dashboard")
    run_state = fields.Selection(
        related="payroll_run_id.state",
        string="Payroll Status",
        readonly=True,
    )
    run_frequency = fields.Char(compute="_compute_dashboard")

    employee_count = fields.Integer(compute="_compute_dashboard")
    employee_complete_count = fields.Integer(compute="_compute_dashboard")
    employee_needs_setup_count = fields.Integer(compute="_compute_dashboard")
    employee_on_hold_count = fields.Integer(compute="_compute_dashboard")
    employee_excluded_count = fields.Integer(compute="_compute_dashboard")

    payroll_employee_count = fields.Integer(compute="_compute_dashboard")
    payroll_payable_count = fields.Integer(compute="_compute_dashboard")
    attention_count = fields.Integer(compute="_compute_dashboard")
    reviewed_count = fields.Integer(compute="_compute_dashboard")
    held_count = fields.Integer(compute="_compute_dashboard")
    ready_count = fields.Integer(compute="_compute_dashboard")
    attendance_confirmed_count = fields.Integer(compute="_compute_dashboard")
    critical_alert_count = fields.Integer(compute="_compute_dashboard")
    warning_alert_count = fields.Integer(compute="_compute_dashboard")
    information_alert_count = fields.Integer(compute="_compute_dashboard")
    attendance_progress = fields.Float(compute="_compute_dashboard")
    review_progress = fields.Float(compute="_compute_dashboard")
    payslip_progress = fields.Float(compute="_compute_dashboard")
    overall_progress = fields.Float(compute="_compute_dashboard")

    expected_hours = fields.Float(compute="_compute_dashboard")
    clocked_hours = fields.Float(compute="_compute_dashboard")
    payable_hours = fields.Float(compute="_compute_dashboard")
    paid_leave_hours = fields.Float(compute="_compute_dashboard")
    unpaid_leave_hours = fields.Float(compute="_compute_dashboard")
    missing_checkout_count = fields.Integer(compute="_compute_dashboard")
    pending_time_off_count = fields.Integer(compute="_compute_dashboard")

    wages_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    additions_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    gross_pay = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    total_deductions = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    net_pay = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    employer_contributions = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    total_company_cost = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )

    paye_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    employee_nis_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    employer_nis_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    health_surcharge_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    employee_statutory_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )
    total_statutory_liability = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )

    bank_employee_count = fields.Integer(compute="_compute_dashboard")
    cash_employee_count = fields.Integer(compute="_compute_dashboard")
    cheque_employee_count = fields.Integer(compute="_compute_dashboard")
    missing_bank_count = fields.Integer(compute="_compute_dashboard")
    bank_transfer_total = fields.Monetary(
        currency_field="currency_id", compute="_compute_dashboard"
    )

    payslip_count = fields.Integer(compute="_compute_dashboard")
    payslip_ready_count = fields.Integer(compute="_compute_dashboard")
    payslip_pending_count = fields.Integer(compute="_compute_dashboard")

    recent_run_ids = fields.Many2many(
        "spx.tt.payroll.run",
        string="Recent Payroll Runs",
        compute="_compute_dashboard",
    )
    payroll_trend_html = fields.Html(
        string="Payroll Cost Trend",
        compute="_compute_dashboard",
        sanitize=False,
    )

    @api.depends()
    def _compute_name(self):
        for dashboard in self:
            dashboard.name = _("Payroll Dashboard")

    @api.model
    def _latest_run(self, company):
        Run = self.env["spx.tt.payroll.run"]
        active_run = Run.search(
            [
                ("company_id", "=", company.id),
                ("state", "not in", ["paid", "cancelled"]),
            ],
            order="payment_date desc, id desc",
            limit=1,
        )
        if active_run:
            return active_run
        return Run.search(
            [
                ("company_id", "=", company.id),
                ("state", "!=", "cancelled"),
            ],
            order="payment_date desc, id desc",
            limit=1,
        )

    def _dashboard_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payroll Dashboard"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "spx_tt_payroll.view_tt_payroll_dashboard_form"
                    ).id,
                    "form",
                )
            ],
            "target": "current",
        }

    @api.model
    def action_open_dashboard(self):
        company = self.env.company
        dashboards = self.search(
            [
                ("company_id", "=", company.id),
                ("create_uid", "=", self.env.uid),
            ],
            order="id desc",
        )
        dashboard = dashboards[:1]
        if dashboard:
            (dashboards - dashboard).unlink()
            selected = dashboard.payroll_run_id
            if not selected or selected.company_id != company:
                dashboard.write({"payroll_run_id": self._latest_run(company).id or False})
        else:
            latest_run = self._latest_run(company)
            dashboard = self.create(
                {
                    "company_id": company.id,
                    "payroll_run_id": latest_run.id or False,
                }
            )
        return dashboard._dashboard_action()

    @api.depends("company_id", "payroll_run_id")
    def _compute_dashboard(self):
        Employee = self.env["hr.employee"]
        Run = self.env["spx.tt.payroll.run"]
        for dashboard in self:
            company = dashboard.company_id or self.env.company
            run = dashboard.payroll_run_id
            if run and run.company_id != company:
                run = self.env["spx.tt.payroll.run"]

            employees = Employee.search(
                [
                    ("company_id", "=", company.id),
                    ("active", "=", True),
                ]
            )
            payroll_employees = employees.filtered(
                lambda emp: emp.tt_payroll_status != "excluded"
            )
            excluded_employees = employees.filtered(
                lambda emp: emp.tt_payroll_status == "excluded"
            )
            complete_employees = payroll_employees.filtered(
                lambda emp: not emp._tt_get_payroll_issues()
            )
            needs_setup_employees = payroll_employees - complete_employees

            dashboard.employee_count = len(payroll_employees)
            dashboard.employee_complete_count = len(complete_employees)
            dashboard.employee_needs_setup_count = len(needs_setup_employees)
            dashboard.employee_on_hold_count = len(
                payroll_employees.filtered(
                    lambda emp: emp.tt_payroll_status == "on_hold"
                )
            )
            dashboard.employee_excluded_count = len(excluded_employees)

            recent_runs = Run.search(
                [
                    ("company_id", "=", company.id),
                    ("state", "!=", "cancelled"),
                ],
                order="payment_date desc, id desc",
                limit=6,
            )
            dashboard.recent_run_ids = recent_runs
            trend_runs = recent_runs.sorted(
                key=lambda recent: (
                    recent.payment_date
                    or recent.date_end
                    or fields.Date.from_string("1900-01-01"),
                    recent.id,
                )
            )
            costs = [
                max(recent.gross_pay + recent.employer_contributions, 0.0)
                for recent in trend_runs
            ]
            max_cost = max(costs or [0.0])
            bars = []
            for recent, cost in zip(trend_runs, costs):
                height = 8 if not max_cost else max(8, round((cost / max_cost) * 100))
                label_date = fields.Date.to_string(
                    recent.payment_date or recent.date_end
                ) if (recent.payment_date or recent.date_end) else ""
                bars.append(
                    '<div class="o_tt_trend_item">'
                    '<div class="o_tt_trend_value">%s</div>'
                    '<div class="o_tt_trend_bar_wrap"><div class="o_tt_trend_bar" style="height:%s%%"></div></div>'
                    '<div class="o_tt_trend_label">%s</div>'
                    '</div>'
                    % (
                        escape(formatLang(self.env, cost, currency_obj=company.currency_id)),
                        height,
                        escape(label_date),
                    )
                )
            dashboard.payroll_trend_html = Markup(
                '<div class="o_tt_trend_chart">%s</div>' % "".join(bars)
            ) if bars else Markup(
                '<div class="o_tt_empty_chart">No completed payroll history yet.</div>'
            )

            if not run:
                dashboard._clear_run_values()
                continue

            lines = run.employee_line_ids
            payable_lines = lines.filtered(
                lambda line: line.review_state not in ("on_hold", "excluded")
            )
            dashboard.has_current_run = True
            dashboard.run_name = run.name
            dashboard.run_period = "%s - %s" % (
                fields.Date.to_string(run.date_start) if run.date_start else "",
                fields.Date.to_string(run.date_end) if run.date_end else "",
            )
            dashboard.run_pay_date = run.payment_date
            dashboard.run_frequency = run.pay_frequency_id.name or ""

            dashboard.payroll_employee_count = len(lines)
            dashboard.payroll_payable_count = len(payable_lines)
            dashboard.attention_count = len(
                lines.filtered(lambda line: line.display_status == "needs_attention")
            )
            dashboard.reviewed_count = len(
                lines.filtered(lambda line: line.display_status == "reviewed")
            )
            dashboard.held_count = len(
                lines.filtered(lambda line: line.review_state == "on_hold")
            )
            dashboard.ready_count = len(
                lines.filtered(lambda line: line.display_status == "ready")
            )
            dashboard.attendance_confirmed_count = len(
                payable_lines.filtered(lambda line: line.attendance_confirmed)
            )

            critical_codes = {
                "missing_salary", "missing_hourly_rate", "missing_bir",
                "missing_nis", "missing_bank", "missing_bank_account",
                "attendance_not_loaded", "missing_work_schedule",
                "missing_checkout", "pending_time_off",
                "time_off_attendance_conflict", "no_attendance",
                "missing_earnings", "missing_statutory_lines",
                "negative_net_pay",
            }
            warning_codes = {
                "pending_overtime", "payable_hours_short",
                "attendance_not_confirmed",
            }
            critical = warning = 0
            for line in payable_lines:
                codes = {item["code"] for item in line._get_attention_items()}
                critical += len(codes & critical_codes)
                warning += len(codes & warning_codes)
            dashboard.critical_alert_count = critical
            dashboard.warning_alert_count = warning
            dashboard.information_alert_count = sum(
                len(line.hours_adjustment_ids) for line in payable_lines
            )

            denominator = len(payable_lines) or 1
            dashboard.attendance_progress = round(
                dashboard.attendance_confirmed_count * 100.0 / denominator, 1
            ) if payable_lines else 0.0
            dashboard.review_progress = round(
                dashboard.reviewed_count * 100.0 / denominator, 1
            ) if payable_lines else 0.0

            dashboard.expected_hours = sum(payable_lines.mapped("scheduled_hours"))
            dashboard.clocked_hours = sum(
                payable_lines.mapped("actual_worked_hours")
            )
            dashboard.payable_hours = sum(payable_lines.mapped("payable_hours"))
            dashboard.paid_leave_hours = sum(
                payable_lines.mapped("paid_leave_hours")
            )
            dashboard.unpaid_leave_hours = sum(
                payable_lines.mapped("unpaid_leave_hours")
            )
            dashboard.missing_checkout_count = sum(
                payable_lines.mapped("incomplete_attendance_count")
            )
            dashboard.pending_time_off_count = sum(
                payable_lines.mapped("pending_time_off_count")
            )

            dashboard.wages_total = sum(
                sum(line.wage_item_ids.mapped("amount")) for line in payable_lines
            )
            dashboard.additions_total = sum(
                sum(line.addition_item_ids.mapped("amount"))
                for line in payable_lines
            )
            dashboard.gross_pay = run.gross_pay
            dashboard.total_deductions = run.total_deductions
            dashboard.net_pay = run.net_pay
            dashboard.employer_contributions = run.employer_contributions
            dashboard.total_company_cost = run.gross_pay + run.employer_contributions

            dashboard.paye_total = sum(payable_lines.mapped("paye_amount"))
            dashboard.employee_nis_total = sum(
                payable_lines.mapped("employee_nis_amount")
            )
            dashboard.employer_nis_total = sum(
                payable_lines.mapped("employer_nis_amount")
            )
            dashboard.health_surcharge_total = sum(
                payable_lines.mapped("health_surcharge_amount")
            )
            dashboard.employee_statutory_total = (
                dashboard.paye_total
                + dashboard.employee_nis_total
                + dashboard.health_surcharge_total
            )
            dashboard.total_statutory_liability = (
                dashboard.employee_statutory_total + dashboard.employer_nis_total
            )

            bank_lines = payable_lines.filtered(
                lambda line: line.payment_method == "bank"
            )
            dashboard.bank_employee_count = len(bank_lines)
            dashboard.cash_employee_count = len(
                payable_lines.filtered(lambda line: line.payment_method == "cash")
            )
            dashboard.cheque_employee_count = len(
                payable_lines.filtered(lambda line: line.payment_method == "cheque")
            )
            dashboard.missing_bank_count = len(
                bank_lines.filtered(
                    lambda line: not line.bank_name or not line.bank_account_number
                )
            )
            dashboard.bank_transfer_total = sum(bank_lines.mapped("net_pay"))

            dashboard.payslip_count = len(payable_lines)
            if run.state in ("approved", "paid"):
                dashboard.payslip_ready_count = len(payable_lines)
                dashboard.payslip_pending_count = 0
            else:
                dashboard.payslip_ready_count = len(
                    payable_lines.filtered(
                        lambda line: line.display_status in ("ready", "reviewed")
                    )
                )
                dashboard.payslip_pending_count = (
                    len(payable_lines) - dashboard.payslip_ready_count
                )
            dashboard.payslip_progress = round(
                dashboard.payslip_ready_count * 100.0 / denominator, 1
            ) if payable_lines else 0.0
            dashboard.overall_progress = round(
                (
                    dashboard.attendance_progress
                    + dashboard.review_progress
                    + dashboard.payslip_progress
                ) / 3.0,
                1,
            )

    def _clear_run_values(self):
        for dashboard in self:
            dashboard.has_current_run = False
            dashboard.run_name = _("No payroll run yet")
            dashboard.run_period = ""
            dashboard.run_pay_date = False
            dashboard.run_frequency = ""
            dashboard.payroll_employee_count = 0
            dashboard.payroll_payable_count = 0
            dashboard.attention_count = 0
            dashboard.reviewed_count = 0
            dashboard.held_count = 0
            dashboard.ready_count = 0
            dashboard.attendance_confirmed_count = 0
            dashboard.critical_alert_count = 0
            dashboard.warning_alert_count = 0
            dashboard.information_alert_count = 0
            dashboard.attendance_progress = 0.0
            dashboard.review_progress = 0.0
            dashboard.payslip_progress = 0.0
            dashboard.overall_progress = 0.0
            dashboard.expected_hours = 0.0
            dashboard.clocked_hours = 0.0
            dashboard.payable_hours = 0.0
            dashboard.paid_leave_hours = 0.0
            dashboard.unpaid_leave_hours = 0.0
            dashboard.missing_checkout_count = 0
            dashboard.pending_time_off_count = 0
            dashboard.wages_total = 0.0
            dashboard.additions_total = 0.0
            dashboard.gross_pay = 0.0
            dashboard.total_deductions = 0.0
            dashboard.net_pay = 0.0
            dashboard.employer_contributions = 0.0
            dashboard.total_company_cost = 0.0
            dashboard.paye_total = 0.0
            dashboard.employee_nis_total = 0.0
            dashboard.employer_nis_total = 0.0
            dashboard.health_surcharge_total = 0.0
            dashboard.employee_statutory_total = 0.0
            dashboard.total_statutory_liability = 0.0
            dashboard.bank_employee_count = 0
            dashboard.cash_employee_count = 0
            dashboard.cheque_employee_count = 0
            dashboard.missing_bank_count = 0
            dashboard.bank_transfer_total = 0.0
            dashboard.payslip_count = 0
            dashboard.payslip_ready_count = 0
            dashboard.payslip_pending_count = 0

    def action_refresh_dashboard(self):
        self.ensure_one()
        self.invalidate_recordset()
        return {
            "type": "ir.actions.client",
            "tag": "soft_reload",
        }

    def action_use_latest_payroll(self):
        self.ensure_one()
        latest_run = self._latest_run(self.company_id or self.env.company)
        self.write({"payroll_run_id": latest_run.id or False})
        return self._dashboard_action()

    def action_select_payroll(self):
        self.ensure_one()
        selected_run = self.payroll_run_id or self._latest_run(
            self.company_id or self.env.company
        )
        if not selected_run:
            raise UserError(_("Create a payroll run before using the payroll selector."))
        wizard = self.env["spx.tt.payroll.dashboard.selector"].create(
            {
                "dashboard_id": self.id,
                "payroll_run_id": selected_run.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Select Payroll"),
            "res_model": "spx.tt.payroll.dashboard.selector",
            "res_id": wizard.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "spx_tt_payroll.view_tt_payroll_dashboard_selector_form"
                    ).id,
                    "form",
                )
            ],
            "target": "new",
        }

    def action_create_payroll_run(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("New Payroll Run"),
            "res_model": "spx.tt.payroll.run",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("spx_tt_payroll.view_tt_payroll_run_form").id,
                    "form",
                )
            ],
            "context": {"default_company_id": self.company_id.id},
            "target": "current",
        }

    def _require_current_run(self):
        self.ensure_one()
        if not self.payroll_run_id:
            raise UserError(_("Create a payroll run first."))
        return self.payroll_run_id

    def action_open_current_run(self):
        run = self._require_current_run()
        return {
            "type": "ir.actions.act_window",
            "name": run.name,
            "res_model": "spx.tt.payroll.run",
            "res_id": run.id,
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("spx_tt_payroll.view_tt_payroll_run_form").id,
                    "form",
                )
            ],
            "target": "current",
        }

    def action_open_payroll_runs(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_runs"
        )
        action["domain"] = [("company_id", "=", self.company_id.id)]
        return action

    def action_open_attention_items(self):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_run_employees"
        )
        action["domain"] = [
            ("run_id", "=", run.id),
            ("display_status", "=", "needs_attention"),
        ]
        action["context"] = {"default_run_id": run.id}
        return action

    def action_open_employees(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_employees"
        )
        action["domain"] = [
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
            ("tt_payroll_status", "!=", "excluded"),
        ]
        return action

    def action_open_employee_setup(self):
        action = self.action_open_employees()
        action["domain"] = action["domain"] + [
            ("tt_payroll_readiness_state", "=", "incomplete")
        ]
        return action

    def action_open_attendance(self):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_attendance.hr_attendance_action"
        )
        employee_ids = run.employee_line_ids.mapped("employee_id").ids
        domain = [("employee_id", "in", employee_ids)]
        if run.date_start:
            start_dt = datetime.combine(run.date_start, time.min)
            domain.append(("check_in", ">=", fields.Datetime.to_string(start_dt)))
        if run.date_end:
            end_dt = datetime.combine(run.date_end + timedelta(days=1), time.min)
            domain.append(("check_in", "<", fields.Datetime.to_string(end_dt)))
        action["domain"] = domain
        return action

    def action_open_time_off(self):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_time_off"
        )
        employee_ids = run.employee_line_ids.mapped("employee_id").ids
        domain = [
            ("employee_id", "in", employee_ids),
            ("state", "in", ["confirm", "validate1", "validate"]),
        ]
        if run.date_start:
            domain.append(("date_to", ">=", fields.Datetime.to_datetime(run.date_start)))
        if run.date_end:
            end_exclusive = fields.Datetime.to_datetime(run.date_end) + timedelta(days=1)
            domain.append(("date_from", "<", end_exclusive))
        action["domain"] = domain
        return action

    def action_open_statutory_breakdown(self):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_run_employees"
        )
        action["domain"] = [("run_id", "=", run.id)]
        action["context"] = {"default_run_id": run.id}
        return action

    def action_open_payments(self):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_run_employees"
        )
        action["domain"] = [
            ("run_id", "=", run.id),
            ("review_state", "not in", ["on_hold", "excluded"]),
        ]
        return action

    def _run_employee_action(self, domain=None, name=None):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_run_employees"
        )
        action["name"] = name or _("Employee Payroll Calculations")
        action["domain"] = [("run_id", "=", run.id)] + (domain or [])
        action["context"] = {"default_run_id": run.id}
        return action

    def action_open_all_calculations(self):
        return self._run_employee_action()

    def action_open_ready_calculations(self):
        return self._run_employee_action(
            [("display_status", "=", "ready")], _("Ready Employees")
        )

    def action_open_reviewed_calculations(self):
        return self._run_employee_action(
            [("display_status", "=", "reviewed")], _("Reviewed Employees")
        )

    def action_open_pending_payslips(self):
        return self._run_employee_action(
            [("display_status", "not in", ["ready", "reviewed"])],
            _("Payslips Pending Review"),
        )

    def action_open_ready_payslips(self):
        return self._run_employee_action(
            [("display_status", "in", ["ready", "reviewed"])],
            _("Payslips Ready"),
        )

    def action_open_missing_bank(self):
        return self._run_employee_action(
            [
                ("payment_method", "=", "bank"),
                "|",
                ("bank_name", "=", False),
                ("bank_account_number", "=", False),
            ],
            _("Employees Missing Bank Details"),
        )

    def action_open_missing_checkouts(self):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_attendance.hr_attendance_action"
        )
        employee_ids = run.employee_line_ids.mapped("employee_id").ids
        domain = [("employee_id", "in", employee_ids), ("check_out", "=", False)]
        if run.date_start:
            start_dt = datetime.combine(run.date_start, time.min)
            domain.append(("check_in", ">=", fields.Datetime.to_string(start_dt)))
        if run.date_end:
            end_dt = datetime.combine(run.date_end + timedelta(days=1), time.min)
            domain.append(("check_in", "<", fields.Datetime.to_string(end_dt)))
        action["domain"] = domain
        return action

    def action_open_pending_time_off(self):
        run = self._require_current_run()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_time_off"
        )
        employee_ids = run.employee_line_ids.mapped("employee_id").ids
        domain = [
            ("employee_id", "in", employee_ids),
            ("state", "in", ["confirm", "validate1"]),
        ]
        if run.date_start:
            domain.append(("date_to", ">=", fields.Datetime.to_datetime(run.date_start)))
        if run.date_end:
            end_exclusive = fields.Datetime.to_datetime(run.date_end) + timedelta(days=1)
            domain.append(("date_from", "<", end_exclusive))
        action["domain"] = domain
        return action

    def action_open_complete_employees(self):
        action = self.action_open_employees()
        action["domain"] += [("tt_payroll_readiness_state", "=", "ready")]
        return action

    def action_open_on_hold_employees(self):
        action = self.action_open_employees()
        action["domain"] = [
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
            ("tt_payroll_status", "=", "on_hold"),
        ]
        return action

    def action_open_excluded_employees(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_employees"
        )
        action["domain"] = [
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
            ("tt_payroll_status", "=", "excluded"),
        ]
        return action

    def action_print_payslips(self):
        return self._require_current_run().action_print_payslips()

    def action_open_settings(self):
        return self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_settings"
        )
