from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    wage_codes = ["BASIC", "REGULAR_HOURS", "OT150", "OT200", "PUBLIC_HOLIDAY"]

    # Salary and attendance-generated wages are controlled by the payroll run,
    # not by recurring employee additions. Keep old profile rows for reference
    # but stop them from being pulled into future payrolls.
    wage_items = env["spx.tt.pay.item"].search([("code", "in", wage_codes)])
    wage_items.write({"recurring_allowed": False})
    recurring_wages = env["spx.tt.employee.pay.item"].search(
        [("pay_item_id", "in", wage_items.ids), ("auto_include", "=", True)]
    )
    if recurring_wages:
        recurring_wages.write(
            {
                "auto_include": False,
                "note": "Disabled automatically: Salary and attendance wages are generated from payable hours.",
            }
        )

    # Rebuild open payroll calculations so zero payable hours immediately gives
    # zero Salary and every employee has exactly one system base-wage line.
    open_lines = env["spx.tt.payroll.run.employee"].search(
        [("run_id.state", "in", ["draft", "attendance_review", "calculated", "under_review"])]
    )
    for line in open_lines:
        line._pull_attendance_snapshot()
        line._rebuild_attendance_earnings()
