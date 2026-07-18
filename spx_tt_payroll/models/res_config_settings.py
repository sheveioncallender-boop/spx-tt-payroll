from odoo import api, fields, models, _


class TTPayrollCompanySettings(models.TransientModel):
    """Simple payroll-only settings screen.

    This intentionally does not inherit Odoo's global res.config.settings model.
    Keeping payroll configuration in its own small workspace avoids loading
    payroll fields throughout the full Odoo Settings application.
    """

    _name = "spx.tt.payroll.company.settings"
    _description = "Trinidad Payroll Company Settings"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    payroll_enabled = fields.Boolean(string="Enable Trinidad Payroll", default=True)
    default_frequency_id = fields.Many2one(
        "spx.tt.pay.frequency",
        string="Default Pay Frequency",
    )
    default_hours_per_day = fields.Float(string="Default Hours per Day", default=8.0)
    default_hours_per_week = fields.Float(string="Default Hours per Week", default=40.0)
    require_review = fields.Boolean(string="Require Payroll Review", default=True)
    require_approval = fields.Boolean(string="Require Payroll Approval", default=True)

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        company = self.env.company
        values.update(self._company_values(company))
        return values

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            for field_name, value in self._company_values(self.company_id).items():
                if field_name != "company_id":
                    setattr(self, field_name, value)

    @api.model
    def _company_values(self, company):
        return {
            "company_id": company.id,
            "payroll_enabled": company.tt_payroll_enabled,
            "default_frequency_id": company.tt_payroll_default_frequency_id.id,
            "default_hours_per_day": company.tt_payroll_default_hours_per_day,
            "default_hours_per_week": company.tt_payroll_default_hours_per_week,
            "require_review": company.tt_payroll_require_review,
            "require_approval": company.tt_payroll_require_approval,
        }

    def action_apply(self):
        self.ensure_one()
        self.company_id.sudo().write(
            {
                "tt_payroll_enabled": self.payroll_enabled,
                "tt_payroll_default_frequency_id": self.default_frequency_id.id,
                "tt_payroll_default_hours_per_day": self.default_hours_per_day,
                "tt_payroll_default_hours_per_week": self.default_hours_per_week,
                "tt_payroll_require_review": self.require_review,
                "tt_payroll_require_approval": self.require_approval,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Payroll Settings Saved"),
                "message": _("The payroll defaults for %s were updated.")
                % self.company_id.display_name,
                "type": "success",
                "sticky": False,
                "next": self.env.ref(
                    "spx_tt_payroll.action_tt_payroll_employees"
                ).read()[0],
            },
        }

    def action_cancel(self):
        return self.env.ref("spx_tt_payroll.action_tt_payroll_employees").read()[0]
