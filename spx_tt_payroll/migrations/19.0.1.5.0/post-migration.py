from odoo import SUPERUSER_ID, api, fields


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Adjustment = env["spx.tt.payroll.hours.adjustment"].sudo().with_context(
        tt_payroll_create_hours_audit=True
    )
    lines = env["spx.tt.payroll.run.employee"].search(
        [("attendance_adjustment_hours", "!=", 0)]
    )
    for line in lines:
        if Adjustment.search_count([("run_employee_id", "=", line.id)]):
            continue
        Adjustment.create(
            {
                "run_employee_id": line.id,
                "previous_adjustment_hours": 0.0,
                "change_hours": line.attendance_adjustment_hours,
                "new_adjustment_hours": line.attendance_adjustment_hours,
                "previous_payable_hours": line.payable_hours,
                "new_payable_hours": line.payable_hours,
                "previous_gross_pay": line.gross_pay,
                "new_gross_pay": line.gross_pay,
                "previous_net_pay": line.net_pay,
                "new_net_pay": line.net_pay,
                "reason": "Existing manual adjustment carried forward during the Phase 4 upgrade",
                "supporting_note": "This entry identifies an adjustment that existed before mandatory reasons were introduced.",
                "adjusted_by": SUPERUSER_ID,
                "adjusted_at": fields.Datetime.now(),
            }
        )
