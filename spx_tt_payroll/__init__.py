from . import models
from . import wizard


def post_init_hook(env):
    """Apply safe defaults to existing companies after installation."""
    monthly = env.ref(
        "spx_tt_payroll.pay_frequency_monthly", raise_if_not_found=False
    )
    if not monthly:
        return

    companies = env["res.company"].search([])
    for company in companies:
        values = {}
        if not company.tt_payroll_default_frequency_id:
            values["tt_payroll_default_frequency_id"] = monthly.id
        if values:
            company.write(values)
