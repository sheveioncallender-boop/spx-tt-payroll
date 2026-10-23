"""Executed by Odoo shell on the disposable CI database before/after upgrade."""
import json
import os

key = "spx_tt_payroll.ci_upgrade_fixture"
if os.environ["TT_UPGRADE_STAGE"] == "before":
    manager = env.ref("base.user_admin")
    manager.group_ids |= env.ref("spx_tt_payroll.group_tt_payroll_manager")
    employee = env["hr.employee"].create({
        "name": "Upgrade preserved employee", "company_id": env.company.id,
        "tt_payroll_status": "active", "tt_pay_type": "monthly", "tt_monthly_salary": 9500,
        "tt_pay_frequency_id": env.ref("spx_tt_payroll.pay_frequency_monthly").id,
        "tt_payment_method": "cash", "tt_bir_number": "CI-BIR", "tt_nis_number": "CI-NIS",
    })
    run = env["spx.tt.payroll.run"].with_context(skip_tt_payroll_auto_load=True).create({
        "company_id": env.company.id, "pay_frequency_id": employee.tt_pay_frequency_id.id,
        "date_start": "2026-01-01", "date_end": "2026-01-31", "payment_date": "2026-01-31",
    })
    line = env["spx.tt.payroll.run.employee"].create({"run_id": run.id, "employee_id": employee.id})
    env["spx.tt.payroll.hours.adjustment.wizard"].create({
        "run_employee_id": line.id, "adjustment_hours": 160,
        "reason": "Migration test reconciliation",
    }).action_apply_adjustment()
    line.action_confirm_attendance()
    run.action_calculate()
    line.action_mark_reviewed()
    run.with_user(manager).action_approve()
    run.with_user(manager).action_mark_paid()
    values = {"run": run.id, "line": line.id, "gross": line.gross_pay,
              "net": line.net_pay, "deductions": line.total_deductions,
              "summary": line._payslip_summary_values(),
              "items": [(item.id, item.amount) for item in line.item_line_ids]}
    env["ir.config_parameter"].sudo().set_param(key, json.dumps(values))
    env.cr.commit()
    print("UPGRADE_FIXTURE_CREATED")
else:
    values = json.loads(env["ir.config_parameter"].sudo().get_param(key))
    run = env["spx.tt.payroll.run"].browse(values["run"])
    line = env["spx.tt.payroll.run.employee"].browse(values["line"])
    assert run.state == "paid"
    assert line.gross_pay == values["gross"]
    assert line.net_pay == values["net"]
    assert line.total_deductions == values["deductions"]
    assert [[item.id, item.amount] for item in line.item_line_ids] == values["items"]
    assert line.locked_summary and line.locked_identity
    assert line._payslip_summary_values() == values["summary"]
    line.employee_id.name = "Renamed after upgrade"
    assert line._payslip_identity()["employee"] == "Upgrade preserved employee"
    assert line._payslip_summary_values() == values["summary"]
    print("UPGRADE_HISTORY_PRESERVED")
