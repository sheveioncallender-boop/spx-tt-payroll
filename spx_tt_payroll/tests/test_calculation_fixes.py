"""Run on an Odoo 19 test database; all records are transaction-isolated."""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


@tagged("post_install", "-at_install")
class TestCalculationFixes(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.monthly = cls.env.ref("spx_tt_payroll.pay_frequency_monthly")
        cls.manager = cls.env.ref("base.user_admin")
        cls.manager.group_ids |= cls.env.ref("spx_tt_payroll.group_tt_payroll_manager")
        cls.employee = cls.env["hr.employee"].create({
            "name": "TT Native Attendance Test", "company_id": cls.env.company.id,
            "tt_payroll_status": "active", "tt_pay_type": "monthly", "tt_monthly_salary": 9500,
            "tt_pay_frequency_id": cls.monthly.id, "tt_payment_method": "cash",
            "tt_bir_number": "TEST-BIR", "tt_nis_number": "TEST-NIS",
        })

    def new_run(self):
        run = self.env["spx.tt.payroll.run"].with_context(skip_tt_payroll_auto_load=True).create({
            "company_id": self.env.company.id, "pay_frequency_id": self.monthly.id,
            "date_start": "2026-01-01", "date_end": "2026-01-31", "payment_date": "2026-01-31",
        })
        line = self.env["spx.tt.payroll.run.employee"].create({"run_id": run.id, "employee_id": self.employee.id})
        return run, line

    def full_pay(self):
        run, line = self.new_run()
        self.env["spx.tt.payroll.hours.adjustment.wizard"].create({
            "run_employee_id": line.id, "adjustment_hours": line.scheduled_hours,
            "reason": "Test department reconciliation",
        }).action_apply_adjustment()
        line.action_confirm_attendance()
        run.action_calculate()
        line.action_mark_reviewed()
        return run, line

    def test_native_clocking_loaded_without_changes(self):
        attendance = self.env["hr.attendance"].create({"employee_id": self.employee.id,
            "check_in": "2026-01-05 08:00:00", "check_out": "2026-01-05 17:00:00"})
        before = attendance.read(["check_in", "check_out", "worked_hours"])[0]
        run, line = self.new_run()
        start, end = line._period_bounds()[3:]
        self.assertAlmostEqual(line.actual_worked_hours, attendance._get_worked_hours_in_range(start, end))
        self.assertEqual(line.attendance_record_count, 1)
        self.assertEqual(attendance.read(["check_in", "check_out", "worked_hours"])[0], before)
        self.env["spx.tt.payroll.hours.adjustment.wizard"].create({"run_employee_id": line.id,
            "adjustment_hours": 2, "reason": "Payroll-only test adjustment"}).action_apply_adjustment()
        self.assertEqual(attendance.read(["check_in", "check_out", "worked_hours"])[0], before)

    def test_corrected_checkout_refreshed(self):
        attendance = self.env["hr.attendance"].create({"employee_id": self.employee.id,
            "check_in": "2026-01-05 08:00:00"})
        _, line = self.new_run()
        self.assertEqual(line.incomplete_attendance_count, 1)
        attendance.check_out = "2026-01-05 17:00:00"
        line.action_refresh_attendance()
        self.assertEqual(line.incomplete_attendance_count, 0)
        self.assertGreater(line.actual_worked_hours, 0)
        self.assertFalse(line.attendance_confirmed)

    def test_native_time_off_approval_and_refresh(self):
        leave_type = self.env["hr.leave.type"].create({
            "name": "TT paid leave test", "requires_allocation": False,
            "leave_validation_type": "hr",
        })
        leave = self.env["hr.leave"].create({
            "name": "Native approval test", "employee_id": self.employee.id,
            "holiday_status_id": leave_type.id,
            "request_date_from": "2026-01-06", "request_date_to": "2026-01-06",
        })
        _, line = self.new_run()
        self.assertEqual(line.pending_time_off_count, 1)
        self.assertEqual(line.paid_leave_hours, 0)
        self.assertEqual(line.gross_pay, 0)
        leave.action_approve()
        self.assertEqual(leave.state, "validate")
        native_values = leave.read(["state", "date_from", "date_to", "number_of_hours"])
        line.action_refresh_attendance()
        self.assertEqual(line.pending_time_off_count, 0)
        self.assertGreater(line.paid_leave_hours, 0)
        self.assertAlmostEqual(line.paid_leave_hours, leave.number_of_hours)
        self.assertAlmostEqual(line.gross_pay, round(9500 * leave.number_of_hours / 160, 2), places=2)
        self.assertEqual(leave.read(["state", "date_from", "date_to", "number_of_hours"]), native_values)

    def test_native_unpaid_time_off_is_not_paid(self):
        leave_type = self.env["hr.leave.type"].create({
            "name": "TT unpaid leave test", "requires_allocation": False,
            "leave_validation_type": "hr", "unpaid": True,
        })
        leave = self.env["hr.leave"].create({
            "name": "Unpaid approval test", "employee_id": self.employee.id,
            "holiday_status_id": leave_type.id,
            "request_date_from": "2026-01-06", "request_date_to": "2026-01-06",
        })
        leave.action_approve()
        _, line = self.new_run()
        self.assertGreater(line.unpaid_leave_hours, 0)
        self.assertAlmostEqual(line.unpaid_leave_hours, leave.number_of_hours)
        self.assertEqual(line.paid_leave_hours, 0)
        self.assertEqual(line.gross_pay, 0)
        self.assertEqual(line.time_off_snapshot_ids.payroll_treatment, "unpaid")

    def test_first_pay_and_live_addition_recalculation(self):
        _, line = self.full_pay()
        self.assertAlmostEqual(line.paye_amount, 407.48, places=2)
        addition = self.env["spx.tt.payroll.run.item"].create({"run_employee_id": line.id,
            "pay_item_id": self.env.ref("spx_tt_payroll.pay_item_phone_allowance").id,
            "calculation_method": "manual", "manual_amount": 250})
        self.assertAlmostEqual(line.paye_amount, 469.98, places=2)
        self.assertEqual(line.review_state, "pending")
        addition.exclude_from_paye = True
        self.assertAlmostEqual(line.paye_amount, 407.48, places=2)
        self.assertAlmostEqual(line.gross_pay, 9750, places=2)

    def test_expired_td1_not_used(self):
        _, line = self.full_pay()
        self.env["spx.tt.employee.statutory.profile"].create({"employee_id": self.employee.id,
            "td1_approved": True, "td1_expiry_date": "2025-12-31", "approved_other_deductions_annual": 12000})
        self.assertAlmostEqual(line.paye_amount, 407.48, places=2)
        self.assertIn("td1_not_current", [issue["code"] for issue in line._get_attention_items()])

    def test_approved_values_and_paid_history_locked(self):
        run, line = self.full_pay()
        run.with_user(self.manager).action_approve()
        saved = line._payslip_summary_values()
        self.env["spx.tt.employee.statutory.profile"].create({"employee_id": self.employee.id,
            "opening_ytd_year": 2026, "opening_net": 50000})
        self.employee.name = "Changed after approval"
        self.assertEqual(line._payslip_summary_values(), saved)
        self.assertEqual(line._payslip_identity()["employee"], "TT Native Attendance Test")
        with self.assertRaises(UserError):
            line.with_context(tt_payroll_allow_locked_write=True).write({"salary_amount": 1})
        with self.assertRaises(UserError):
            run.write({"payment_date": "2026-02-01"})
        with self.assertRaises(UserError):
            self.env["spx.tt.payroll.run.item"].create({"run_employee_id": line.id,
                "pay_item_id": self.env.ref("spx_tt_payroll.pay_item_phone_allowance").id, "manual_amount": 100})
        run.with_user(self.manager).action_mark_paid()
        with self.assertRaises(UserError):
            run.with_user(self.manager).action_reset_to_draft()

    def test_direct_state_and_forged_hours_context_rejected(self):
        run, line = self.new_run()
        with self.assertRaises(UserError):
            run.write({"state": "approved"})
        with self.assertRaises(UserError):
            line.with_context(tt_payroll_internal_write=True).write({"attendance_adjustment_hours": 8})
        with self.assertRaises(UserError):
            line.write({"payable_hours": 160})

    def test_audited_short_hours_can_be_reviewed(self):
        run, line = self.new_run()
        self.env["spx.tt.payroll.hours.adjustment.wizard"].create({"run_employee_id": line.id,
            "adjustment_hours": 140, "reason": "Confirmed short month"}).action_apply_adjustment()
        line.attendance_review_note = "Twenty hours were not worked; pay the confirmed 140 hours."
        line.action_confirm_attendance()
        run.action_calculate()
        line.action_mark_reviewed()
        self.assertAlmostEqual(line.gross_pay, 8312.50, places=2)
        self.assertEqual(line.review_state, "reviewed")

    def test_existing_employee_not_duplicated_when_generated_again(self):
        run, _ = self.new_run()
        run.action_load_employees()
        self.assertEqual(len(run.employee_line_ids.filtered(lambda row: row.employee_id == self.employee)), 1)

    def test_fortnightly_half_cent_lookup(self):
        run, line = self.new_run()
        # A real fortnightly run must be created with that frequency initially.
        other = self.env["spx.tt.pay.frequency"].search([("code", "=", "FORTNIGHTLY")], limit=1)
        second = self.env["spx.tt.payroll.run"].with_context(skip_tt_payroll_auto_load=True).create({
            "company_id": self.env.company.id, "pay_frequency_id": other.id,
            "date_start": "2026-01-05", "date_end": "2026-01-18", "payment_date": "2026-01-18"})
        entry = self.env["spx.tt.payroll.run.employee"].create({"run_id": second.id, "employee_id": self.employee.id})
        self.assertEqual(entry._find_nis_class(679.99)["name"], "II")
