from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    open_states = ["draft", "attendance_review", "calculated", "under_review"]
    lines = env["spx.tt.payroll.run.employee"].sudo().search(
        [("run_id.state", "in", open_states)]
    )
    for line in lines:
        line._pull_attendance_snapshot()
        line._rebuild_attendance_earnings()
