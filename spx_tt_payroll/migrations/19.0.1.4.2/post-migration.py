from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Recalculate only open payrolls using the corrected period PAYE method.
    # Approved and paid payrolls remain immutable historical records.
    open_lines = env["spx.tt.payroll.run.employee"].search(
        [
            (
                "run_id.state",
                "in",
                ["draft", "attendance_review", "calculated", "under_review"],
            )
        ]
    )
    for line in open_lines:
        line._calculate_statutory_items()
