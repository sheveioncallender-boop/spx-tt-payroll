from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TTEmployeeStatutoryProfile(models.Model):
    _name = "spx.tt.employee.statutory.profile"
    _description = "Employee PAYE and Statutory Profile"
    _rec_name = "employee_id"
    _order = "employee_id"
    _check_company_auto = True

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="employee_id.company_id",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    resident = fields.Boolean(
        string="Resident Individual",
        default=True,
        help="Resident employees receive the statutory personal allowance unless an override is entered.",
    )
    paye_exempt = fields.Boolean(string="PAYE Exempt")
    td1_approved = fields.Boolean(string="TD1 Confirmed")
    td1_effective_date = fields.Date(string="TD1 Effective Date")
    td1_expiry_date = fields.Date(string="TD1 Expiry Date")
    personal_allowance_override = fields.Monetary(
        string="Annual Personal Allowance Override",
        currency_field="currency_id",
        help="Leave at zero to use the statutory allowance for the payroll year.",
    )
    approved_pension_annuity_annual = fields.Monetary(
        string="Approved Annual Pension / Annuity",
        currency_field="currency_id",
        help="Approved annual pension, annuity, or tax-savings deductions. This is combined with the 70% NIS relief and limited by the statutory cap.",
    )
    approved_other_deductions_annual = fields.Monetary(
        string="Other Approved Annual Deductions",
        currency_field="currency_id",
        help="Other annual deductions approved on the employee's TD1, excluding personal allowance, pension/annuity, and NIS relief.",
    )
    approved_tax_credits_annual = fields.Monetary(
        string="Approved Annual Tax Credits",
        currency_field="currency_id",
    )

    retirement_pension_recipient = fields.Boolean(
        string="Receives NIS Retirement Pension",
        help="Used to apply Class Z employer-only NIS where applicable.",
    )
    pension_only_income = fields.Boolean(
        string="Only Source of Income is Pension",
        help="Health Surcharge is not deducted where the employee's only source of income is pension.",
    )

    opening_ytd_year = fields.Integer(string="Opening YTD Year")
    opening_period_count = fields.Integer(
        string="Completed Pay Periods Before Odoo",
        help="Number of payroll periods already completed in the opening year before this module began calculating payroll.",
    )
    opening_taxable_earnings = fields.Monetary(
        string="Opening Taxable Earnings",
        currency_field="currency_id",
    )
    opening_paye = fields.Monetary(string="Opening PAYE", currency_field="currency_id")
    opening_employee_nis = fields.Monetary(
        string="Opening Employee NIS",
        currency_field="currency_id",
    )
    opening_health_surcharge = fields.Monetary(
        string="Opening Health Surcharge",
        currency_field="currency_id",
    )
    opening_income = fields.Monetary(
        string="Opening Income / Wages",
        currency_field="currency_id",
        help="Wages already paid in the opening payroll year before TT Payroll was used.",
    )
    opening_additions = fields.Monetary(
        string="Opening Additions",
        currency_field="currency_id",
    )
    opening_gross = fields.Monetary(
        string="Opening Gross Pay",
        currency_field="currency_id",
    )
    opening_other_deductions = fields.Monetary(
        string="Opening Other Deductions",
        currency_field="currency_id",
        help="Non-statutory deductions already taken in the opening payroll year.",
    )
    opening_loans = fields.Monetary(
        string="Opening Loan Payments",
        currency_field="currency_id",
    )
    opening_net = fields.Monetary(
        string="Opening Net Pay",
        currency_field="currency_id",
    )
    notes = fields.Text()

    _sql_constraints = [
        (
            "spx_tt_employee_statutory_profile_unique",
            "unique(employee_id)",
            "Each employee can only have one PAYE and statutory profile.",
        )
    ]

    @api.constrains(
        "personal_allowance_override",
        "approved_pension_annuity_annual",
        "approved_other_deductions_annual",
        "approved_tax_credits_annual",
        "opening_period_count",
        "opening_taxable_earnings",
        "opening_paye",
        "opening_employee_nis",
        "opening_health_surcharge",
        "opening_income",
        "opening_additions",
        "opening_gross",
        "opening_other_deductions",
        "opening_loans",
        "opening_net",
    )
    def _check_non_negative_values(self):
        for record in self:
            values = [
                record.personal_allowance_override,
                record.approved_pension_annuity_annual,
                record.approved_other_deductions_annual,
                record.approved_tax_credits_annual,
                record.opening_period_count,
                record.opening_taxable_earnings,
                record.opening_paye,
                record.opening_employee_nis,
                record.opening_health_surcharge,
                record.opening_income,
                record.opening_additions,
                record.opening_gross,
                record.opening_other_deductions,
                record.opening_loans,
                record.opening_net,
            ]
            if any(value < 0 for value in values):
                raise ValidationError(_("Statutory profile amounts and period counts cannot be negative."))

    @api.constrains("td1_effective_date", "td1_expiry_date")
    def _check_td1_dates(self):
        for record in self:
            if (
                record.td1_effective_date
                and record.td1_expiry_date
                and record.td1_expiry_date < record.td1_effective_date
            ):
                raise ValidationError(_("The TD1 expiry date cannot be before its effective date."))
