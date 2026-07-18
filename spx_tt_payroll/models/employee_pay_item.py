from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TTEmployeePayItem(models.Model):
    _name = "spx.tt.employee.pay.item"
    _description = "Employee Recurring Payroll Item"
    _order = "employee_id, sequence, id"
    _check_company_auto = True

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company", related="employee_id.company_id", store=True, index=True
    )
    pay_item_id = fields.Many2one(
        "spx.tt.pay.item",
        required=True,
        ondelete="restrict",
        domain="[('recurring_allowed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    category = fields.Selection(related="pay_item_id.category", store=True)
    calculation_method = fields.Selection(
        related="pay_item_id.calculation_method", store=True
    )
    amount = fields.Monetary(currency_field="currency_id")
    percentage = fields.Float()
    quantity = fields.Float(default=1.0)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )
    reference = fields.Char(
        string="Reference",
        help="Optional loan, policy, membership, or authorization reference.",
    )
    original_balance = fields.Monetary(
        string="Original Balance", currency_field="currency_id"
    )
    remaining_balance = fields.Monetary(
        string="Remaining Balance", currency_field="currency_id"
    )
    show_on_payslip = fields.Boolean(string="Show on Payslip", default=True)
    exclude_from_paye = fields.Boolean(
        string="Exclude from PAYE",
        default=False,
        help="Leave off for normal allowances and additions. Enable only for an approved PAYE-exempt earning.",
    )
    auto_include = fields.Boolean(
        string="Add Automatically",
        default=True,
        help="Add this item automatically whenever the employee is included in a matching payroll run.",
    )
    pay_frequency_ids = fields.Many2many(
        "spx.tt.pay.frequency",
        "spx_tt_employee_item_frequency_rel",
        "employee_item_id",
        "frequency_id",
        string="Pay Frequencies",
        help="Leave blank to add this item for every pay frequency.",
    )
    start_date = fields.Date()
    end_date = fields.Date()
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    note = fields.Char()

    @api.onchange("pay_item_id")
    def _onchange_pay_item_id(self):
        if self.pay_item_id:
            self.amount = self.pay_item_id.default_amount
            self.percentage = self.pay_item_id.default_percentage
            self.exclude_from_paye = self.pay_item_id.exclude_from_paye

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        PayItem = self.env["spx.tt.pay.item"]
        for vals in vals_list:
            vals = dict(vals)
            pay_item_id = vals.get("pay_item_id")
            if pay_item_id and "exclude_from_paye" not in vals:
                pay_item = PayItem.browse(pay_item_id).exists()
                if pay_item:
                    vals["exclude_from_paye"] = pay_item.exclude_from_paye
            prepared.append(vals)
        return super().create(prepared)

    @api.constrains(
        "amount",
        "percentage",
        "quantity",
        "original_balance",
        "remaining_balance",
    )
    def _check_non_negative_values(self):
        for record in self:
            values = [
                record.amount,
                record.percentage,
                record.quantity,
                record.original_balance,
                record.remaining_balance,
            ]
            if any(value < 0 for value in values):
                raise ValidationError(
                    "Payroll item amounts, percentages, quantities, and balances cannot be negative."
                )

    @api.constrains("original_balance", "remaining_balance")
    def _check_remaining_balance(self):
        for record in self:
            if (
                record.original_balance > 0
                and record.remaining_balance > record.original_balance
            ):
                raise ValidationError(
                    "The remaining balance cannot exceed the original balance."
                )

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError("The end date cannot be before the start date.")
