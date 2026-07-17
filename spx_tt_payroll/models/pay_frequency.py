from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TTPayFrequency(models.Model):
    _name = "spx.tt.pay.frequency"
    _description = "Trinidad Payroll Pay Frequency"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    periods_per_year = fields.Integer(required=True, default=12)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()

    _sql_constraints = [
        (
            "spx_tt_pay_frequency_code_unique",
            "unique(code)",
            "The pay frequency code must be unique.",
        )
    ]

    @api.constrains("periods_per_year")
    def _check_periods_per_year(self):
        for record in self:
            if not 1 <= record.periods_per_year <= 366:
                raise ValidationError(
                    "Periods per year must be between 1 and 366."
                )
