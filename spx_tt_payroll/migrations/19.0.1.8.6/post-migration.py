"""Freeze legacy completed payslips without recalculating their financial values."""
import json
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for line in env["spx.tt.payroll.run.employee"].search([
        ("run_id.state", "in", ["approved", "paid"]), ("locked_summary", "=", False)
    ]):
        # New snapshot columns only. Values capture the legacy payslip at upgrade,
        # not a reconstruction of changes made before this version was installed.
        cr.execute("""UPDATE spx_tt_payroll_run_employee
                      SET locked_summary=%s::jsonb, locked_identity=%s::jsonb WHERE id=%s""",
                   [json.dumps(line._payslip_summary_values()), json.dumps(line._payslip_identity()), line.id])
    # Mark unfinished work for a fresh calculation/review using the new rules.
    cr.execute("""UPDATE spx_tt_payroll_run_employee SET review_state='pending'
                  WHERE review_state='reviewed' AND run_id IN
                  (SELECT id FROM spx_tt_payroll_run WHERE state NOT IN ('approved','paid','cancelled'))""")
