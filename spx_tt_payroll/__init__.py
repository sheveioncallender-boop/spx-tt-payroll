from odoo.fields import Command

from . import models
from . import wizard


def post_init_hook(env):
    """Apply safe defaults after every module table and data file exists."""
    monthly = env.ref(
        "spx_tt_payroll.pay_frequency_monthly", raise_if_not_found=False
    )
    if monthly:
        companies = env["res.company"].sudo().search([])
        for company in companies:
            values = {}
            if not company.tt_payroll_default_frequency_id:
                values["tt_payroll_default_frequency_id"] = monthly.id
            if values:
                company.write(values)

        enrolled_employees = env["hr.employee"].sudo().search(
            [("tt_payroll_enabled", "=", True)]
        )
        for employee in enrolled_employees:
            values = {}
            company = employee.company_id or env.company
            if not employee.tt_pay_frequency_id:
                values["tt_pay_frequency_id"] = (
                    company.tt_payroll_default_frequency_id.id or monthly.id
                )
            if not employee.tt_normal_hours_per_day:
                values["tt_normal_hours_per_day"] = (
                    company.tt_payroll_default_hours_per_day or 8.0
                )
            if not employee.tt_normal_hours_per_week:
                values["tt_normal_hours_per_week"] = (
                    company.tt_payroll_default_hours_per_week or 40.0
                )
            if values:
                employee.write(values)

    # Ensure the standard Odoo administrator can open Payroll immediately.
    administrator = env.ref("base.user_admin", raise_if_not_found=False)
    payroll_manager = env.ref(
        "spx_tt_payroll.group_tt_payroll_manager", raise_if_not_found=False
    )
    if administrator and payroll_manager and payroll_manager not in administrator.group_ids:
        administrator.sudo().write(
            {"group_ids": [Command.link(payroll_manager.id)]}
        )
