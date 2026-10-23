from odoo import api, fields, models
from odoo.exceptions import UserError


class TTPayItem(models.Model):
    _name = "spx.tt.pay.item"
    _description = "Trinidad Payroll Earning or Deduction"
    _order = "sequence, name"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    category = fields.Selection(
        [
            ("earning", "Earning"),
            ("deduction", "Deduction"),
            ("employer", "Employer Contribution"),
        ],
        required=True,
        default="earning",
        index=True,
    )
    calculation_method = fields.Selection(
        [
            ("fixed", "Fixed Amount"),
            ("percentage", "Percentage"),
            ("hours", "Hours × Rate"),
            ("manual", "Entered During Payroll"),
        ],
        required=True,
        default="fixed",
    )
    default_amount = fields.Monetary(currency_field="currency_id")
    default_percentage = fields.Float()
    taxable = fields.Boolean(
        default=True,
        help="Technical compatibility field. Earnings are taxable for PAYE unless Exclude from PAYE is enabled.",
    )
    exclude_from_paye = fields.Boolean(
        string="Exclude from PAYE",
        default=False,
        help="Enable only where this earning has an approved PAYE exemption. Gross pay is unchanged; only PAYE taxable earnings are reduced.",
    )
    nis_applicable = fields.Boolean(
        default=True,
        help="Whether this earning normally forms part of NIS insurable earnings.",
    )
    recurring_allowed = fields.Boolean(default=True)
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
    company_id = fields.Many2one(
        "res.company",
        help="Leave blank to make this item available to every company.",
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_system = fields.Boolean(
        default=False,
        help="System items can be edited or archived but are protected from deletion.",
    )
    description = fields.Text()

    _spx_tt_pay_item_code_company_unique = models.Constraint('unique(code, company_id)', 'The payroll item code must be unique for the selected company.')

    @api.depends("company_id")
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.company_id.currency_id or self.env.company.currency_id

    @api.constrains("code", "company_id")
    def _check_global_code_unique(self):
        for record in self:
            if record.company_id:
                continue
            duplicate = self.search_count(
                [("id", "!=", record.id), ("code", "=", record.code), ("company_id", "=", False)]
            )
            if duplicate:
                raise UserError("A global payroll item with this code already exists.")

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if "exclude_from_paye" in vals and "taxable" not in vals:
                vals["taxable"] = not vals["exclude_from_paye"]
            elif "taxable" in vals and "exclude_from_paye" not in vals:
                vals["exclude_from_paye"] = not vals["taxable"]
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        vals = dict(vals)
        if "exclude_from_paye" in vals and "taxable" not in vals:
            vals["taxable"] = not vals["exclude_from_paye"]
        elif "taxable" in vals and "exclude_from_paye" not in vals:
            vals["exclude_from_paye"] = not vals["taxable"]
        return super().write(vals)

    def unlink(self):
        protected = self.filtered("is_system")
        if protected:
            raise UserError(
                "Standard payroll items cannot be deleted. Archive them if they are not used."
            )
        return super().unlink()
