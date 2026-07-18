from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TTPayrollRunItem(models.Model):
    _name = "spx.tt.payroll.run.item"
    _description = "Payroll Run Earning or Deduction"
    _rec_name = "description"
    _order = "sequence, id"
    _check_company_auto = True

    run_employee_id = fields.Many2one(
        "spx.tt.payroll.run.employee",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    run_id = fields.Many2one(
        "spx.tt.payroll.run",
        related="run_employee_id.run_id",
        store=True,
        index=True,
    )
    run_state = fields.Selection(related="run_id.state", readonly=True)
    employee_id = fields.Many2one(
        "hr.employee",
        related="run_employee_id.employee_id",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="run_employee_id.company_id",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="run_employee_id.currency_id",
        readonly=True,
    )
    pay_item_id = fields.Many2one(
        "spx.tt.pay.item",
        string="Payroll Item",
        required=True,
        ondelete="restrict",
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    employee_pay_item_id = fields.Many2one(
        "spx.tt.employee.pay.item",
        string="Employee Recurring Item",
        ondelete="set null",
        copy=False,
    )
    description = fields.Char(required=True)
    category = fields.Selection(
        [
            ("earning", "Earning"),
            ("deduction", "Deduction"),
            ("employer", "Employer Contribution"),
        ],
        required=True,
        index=True,
    )
    calculation_method = fields.Selection(
        [
            ("fixed", "Rate × Quantity"),
            ("percentage", "Percentage"),
            ("hours", "Hours × Rate"),
            ("manual", "Manual Amount"),
        ],
        required=True,
        default="manual",
    )
    rate = fields.Monetary(currency_field="currency_id")
    quantity = fields.Float(default=1.0)
    factor = fields.Float(default=1.0)
    percentage = fields.Float()
    base_amount = fields.Monetary(currency_field="currency_id")
    manual_amount = fields.Monetary(string="Manual Amount", currency_field="currency_id")
    amount = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True,
    )
    source = fields.Selection(
        [
            ("basic", "Basic Pay (Legacy)"),
            ("salary", "Salary / Regular Hours"),
            ("recurring", "Employee Setup"),
            ("manual", "Manual Entry"),
            ("attendance", "Attendance"),
            ("statutory", "Statutory"),
        ],
        default="manual",
        required=True,
    )
    taxable = fields.Boolean(default=True)
    nis_applicable = fields.Boolean(string="NIS Applicable", default=True)
    statutory_code = fields.Selection(
        [
            ("none", "Not Statutory"),
            ("paye", "PAYE"),
            ("employee_nis", "Employee NIS"),
            ("employer_nis", "Employer NIS"),
            ("health_surcharge", "Health Surcharge"),
        ],
        default="none",
        required=True,
    )
    reference = fields.Char()
    remaining_balance = fields.Monetary(currency_field="currency_id")
    show_on_payslip = fields.Boolean(default=True)
    payslip_section = fields.Selection(
        [
            ("wage", "Wages"),
            ("addition", "Additions"),
            ("tax", "Taxes"),
            ("deduction", "Deductions"),
            ("loan", "Loans"),
            ("employer", "Employer Contributions"),
        ],
        string="Payslip Section",
        compute="_compute_payslip_section",
        store=True,
        index=True,
    )
    note = fields.Char()
    sequence = fields.Integer(default=10)

    @api.depends("pay_item_id.code", "category", "statutory_code")
    def _compute_payslip_section(self):
        wage_codes = {"BASIC", "REGULAR_HOURS", "OT150", "OT200", "PUBLIC_HOLIDAY"}
        loan_codes = {"LOAN", "SALARY_ADVANCE"}
        tax_codes = {"paye", "employee_nis", "health_surcharge"}
        for item in self:
            code = item.pay_item_id.code or ""
            if item.statutory_code in tax_codes:
                item.payslip_section = "tax"
            elif item.category == "employer" or item.statutory_code == "employer_nis":
                item.payslip_section = "employer"
            elif code in loan_codes:
                item.payslip_section = "loan"
            elif code in wage_codes:
                item.payslip_section = "wage"
            elif item.category == "earning":
                item.payslip_section = "addition"
            else:
                item.payslip_section = "deduction"

    @api.depends(
        "calculation_method",
        "rate",
        "quantity",
        "factor",
        "percentage",
        "base_amount",
        "manual_amount",
    )
    def _compute_amount(self):
        for item in self:
            if item.calculation_method in ("fixed", "hours"):
                item.amount = item.rate * item.quantity * item.factor
            elif item.calculation_method == "percentage":
                item.amount = (
                    item.base_amount
                    * (item.percentage / 100.0)
                    * item.quantity
                    * item.factor
                )
            else:
                item.amount = item.manual_amount

    @api.onchange("pay_item_id")
    def _onchange_pay_item_id(self):
        if not self.pay_item_id:
            return
        pay_item = self.pay_item_id
        self.description = pay_item.name
        self.category = pay_item.category
        self.calculation_method = pay_item.calculation_method
        self.rate = pay_item.default_amount
        self.manual_amount = pay_item.default_amount
        self.percentage = pay_item.default_percentage
        self.taxable = pay_item.taxable
        self.nis_applicable = pay_item.nis_applicable
        self.statutory_code = pay_item.statutory_code
        self.sequence = pay_item.sequence

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            pay_item_id = vals.get("pay_item_id")
            pay_item = (
                self.env["spx.tt.pay.item"].browse(pay_item_id).exists()
                if pay_item_id
                else self.env["spx.tt.pay.item"]
            )
            if pay_item:
                vals.setdefault("description", pay_item.name)
                vals.setdefault("category", pay_item.category)
                vals.setdefault("calculation_method", pay_item.calculation_method)
                vals.setdefault("rate", pay_item.default_amount)
                vals.setdefault("manual_amount", pay_item.default_amount)
                vals.setdefault("percentage", pay_item.default_percentage)
                vals.setdefault("taxable", pay_item.taxable)
                vals.setdefault("nis_applicable", pay_item.nis_applicable)
                vals.setdefault("statutory_code", pay_item.statutory_code)
                vals.setdefault("sequence", pay_item.sequence)
            prepared.append(vals)
        return super().create(prepared)

    def _check_editable(self):
        if any(item.run_state in ("approved", "paid", "cancelled") for item in self):
            raise UserError(_("Approved, paid, or cancelled payroll items are locked."))

    def write(self, vals):
        self._check_editable()
        return super().write(vals)

    def unlink(self):
        self._check_editable()
        return super().unlink()
