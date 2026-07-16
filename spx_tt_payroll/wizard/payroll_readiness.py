from odoo import api, fields, models


class TTPayrollReadiness(models.TransientModel):
    _name = "spx.tt.payroll.readiness"
    _description = "Trinidad Payroll Checklist"
    _rec_name = "name"

    name = fields.Char(default="Payroll Checklist", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    employee_total = fields.Integer(readonly=True)
    ready_count = fields.Integer(readonly=True)
    incomplete_count = fields.Integer(readonly=True)
    missing_frequency_count = fields.Integer(readonly=True)
    missing_pay_count = fields.Integer(readonly=True)
    missing_bir_count = fields.Integer(readonly=True)
    missing_nis_count = fields.Integer(readonly=True)
    missing_schedule_count = fields.Integer(readonly=True)
    missing_bank_count = fields.Integer(readonly=True)

    @api.model
    def action_open_readiness(self):
        """Create a fresh checklist and open it safely."""
        wizard = self.create({})
        action = self.env.ref(
            "spx_tt_payroll.action_tt_payroll_readiness_window"
        ).read()[0]
        action["res_id"] = wizard.id
        return action

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        company = self.env.company
        values.update(self._get_readiness_values(company))
        return values

    def _employees(self):
        self.ensure_one()
        return self.env["hr.employee"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("active", "=", True),
                ("tt_payroll_status", "!=", "excluded"),
            ]
        )

    @api.model
    def _get_readiness_values(self, company):
        employees = self.env["hr.employee"].search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
                ("tt_payroll_status", "!=", "excluded"),
            ]
        )
        ready = employees.filtered(
            lambda employee: not employee._tt_get_payroll_issues()
        )
        return {
            "name": "Payroll Checklist",
            "company_id": company.id,
            "employee_total": len(employees),
            "ready_count": len(ready),
            "incomplete_count": len(employees - ready),
            "missing_frequency_count": len(
                employees.filtered(lambda employee: not employee.tt_pay_frequency_id)
            ),
            "missing_pay_count": len(
                employees.filtered(self._employee_missing_pay_information)
            ),
            "missing_bir_count": len(
                employees.filtered(lambda employee: not employee.tt_bir_number)
            ),
            "missing_nis_count": len(
                employees.filtered(
                    lambda employee: not employee.tt_nis_exempt
                    and not employee.tt_nis_number
                )
            ),
            "missing_schedule_count": len(
                employees.filtered(lambda employee: not employee.resource_calendar_id)
            ),
            "missing_bank_count": len(
                employees.filtered(
                    lambda employee: employee.tt_payment_method == "bank"
                    and not employee.primary_bank_account_id
                )
            ),
        }

    @api.model
    def _employee_missing_pay_information(self, employee):
        if not employee.tt_pay_type:
            return True
        amount_by_type = {
            "monthly": employee.tt_monthly_salary,
            "weekly": employee.tt_weekly_salary,
            "daily": employee.tt_daily_rate,
            "hourly": employee.tt_hourly_rate,
        }
        return amount_by_type.get(employee.tt_pay_type, 0.0) <= 0

    def _employee_action(self, domain):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "spx_tt_payroll.action_tt_payroll_employees"
        )
        action["name"] = "Employees"
        action["view_mode"] = "list,form"
        action["domain"] = [
            ("company_id", "=", self.company_id.id),
            ("active", "=", True),
            ("tt_payroll_status", "!=", "excluded"),
        ] + domain
        return action

    def action_open_all(self):
        return self._employee_action([])

    def action_open_ready(self):
        employee_ids = self._employees().filtered(
            lambda employee: not employee._tt_get_payroll_issues()
        ).ids
        return self._employee_action([("id", "in", employee_ids)])

    def action_open_incomplete(self):
        employee_ids = self._employees().filtered(
            lambda employee: bool(employee._tt_get_payroll_issues())
        ).ids
        return self._employee_action([("id", "in", employee_ids)])

    def action_open_missing_frequency(self):
        return self._employee_action([("tt_pay_frequency_id", "=", False)])

    def action_open_missing_pay(self):
        employee_ids = self._employees().filtered(
            self._employee_missing_pay_information
        ).ids
        return self._employee_action([("id", "in", employee_ids)])

    def action_open_missing_bir(self):
        return self._employee_action([("tt_bir_number", "=", False)])

    def action_open_missing_nis(self):
        return self._employee_action(
            [("tt_nis_exempt", "=", False), ("tt_nis_number", "=", False)]
        )

    def action_open_missing_schedule(self):
        return self._employee_action([("resource_calendar_id", "=", False)])

    def action_open_missing_bank(self):
        employee_ids = self._employees().filtered(
            lambda employee: employee.tt_payment_method == "bank"
            and not employee.primary_bank_account_id
        ).ids
        return self._employee_action([("id", "in", employee_ids)])

    def action_refresh(self):
        self.ensure_one()
        self.write(self._get_readiness_values(self.company_id))
        return {
            "type": "ir.actions.act_window",
            "name": "Payroll Checklist",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }
