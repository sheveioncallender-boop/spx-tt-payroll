from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    PayItem = env["spx.tt.pay.item"].with_context(active_test=False)
    for item in PayItem.search([]):
        item.with_context(tracking_disable=True).write(
            {"exclude_from_paye": not item.taxable}
        )

    EmployeeItem = env["spx.tt.employee.pay.item"].with_context(active_test=False)
    for item in EmployeeItem.search([]):
        item.with_context(tracking_disable=True).write(
            {"exclude_from_paye": item.pay_item_id.exclude_from_paye}
        )

    RunItem = env["spx.tt.payroll.run.item"]
    open_states = ["draft", "attendance_review", "calculated", "under_review"]
    for item in RunItem.search(
        [("category", "=", "earning"), ("run_state", "in", open_states)]
    ):
        item.with_context(tracking_disable=True).write(
            {"exclude_from_paye": not item.taxable}
        )

    open_lines = env["spx.tt.payroll.run.employee"].search(
        [("run_id.state", "in", open_states)]
    )
    for line in open_lines:
        line._calculate_statutory_items()
