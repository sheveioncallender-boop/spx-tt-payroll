from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Recalculate open payrolls with the automatic PAYE, NIS, Employer NIS,
    # and Health Surcharge engine. Approved and paid payrolls are preserved.
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
        line._load_default_items()
        line._calculate_statutory_items()
