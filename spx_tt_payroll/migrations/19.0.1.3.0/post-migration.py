from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Rename the original system earning without changing its external ID.
    salary_item = env.ref("spx_tt_payroll.pay_item_basic", raise_if_not_found=False)
    if salary_item:
        salary_item.write({"name": "Salary"})

    # Convert the older four-option pay setup into the simpler Salaried/Hourly
    # structure while preserving the original database columns for compatibility.
    employees = env["hr.employee"].with_context(active_test=False).search([])
    for employee in employees:
        vals = {}
        if employee.tt_pay_type == "weekly":
            if not employee.tt_monthly_salary and employee.tt_weekly_salary:
                vals["tt_monthly_salary"] = employee.tt_weekly_salary * 52.0 / 12.0
            vals["tt_pay_type"] = "monthly"
        elif employee.tt_pay_type == "daily":
            if not employee.tt_hourly_rate and employee.tt_daily_rate:
                hours = employee.tt_normal_hours_per_day or 8.0
                vals["tt_hourly_rate"] = employee.tt_daily_rate / hours
            vals["tt_pay_type"] = "hourly"
        if vals:
            employee.write(vals)

    # Existing Phase 2A run employees receive the new snapshot fields. Their
    # existing earning lines are not deleted; the user can refresh attendance
    # when ready.
    run_lines = env["spx.tt.payroll.run.employee"].search([])
    for line in run_lines:
        vals = {}
        if not line.pay_basis:
            vals["pay_basis"] = (
                "hourly" if line.pay_type in ("hourly", "daily") else "salary"
            )
        basis = vals.get("pay_basis") or line.pay_basis
        if basis == "salary" and not line.salary_amount:
            vals["salary_amount"] = line.base_rate
            vals["period_salary"] = line._period_salary_from_monthly(
                line.base_rate, line.run_id
            )
        elif basis == "hourly" and not line.hourly_rate:
            vals["hourly_rate"] = line.base_rate
        if vals:
            line.with_context(tt_payroll_internal_write=True, tt_payroll_allow_locked_write=True).write(vals)
