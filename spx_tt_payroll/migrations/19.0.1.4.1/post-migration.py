from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    open_lines = env["spx.tt.payroll.run.employee"].search(
        [("run_id.state", "in", ["draft", "attendance_review", "calculated", "under_review"])]
    )
    for line in open_lines:
        line._recalculate_payable_hours()
        line._rebuild_attendance_earnings()
        line._calculate_statutory_items()
