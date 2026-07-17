from odoo.tests.common import TransactionCase


class TestTTPayrollRun(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.monthly = cls.env.ref("spx_tt_payroll.pay_frequency_monthly")
        cls.phone_allowance = cls.env.ref("spx_tt_payroll.pay_item_phone_allowance")
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Payroll Run Test Employee",
                "company_id": cls.env.company.id,
                "tt_payroll_status": "active",
                "tt_pay_type": "monthly",
                "tt_pay_frequency_id": cls.monthly.id,
                "tt_monthly_salary": 9500.0,
                "tt_payment_method": "cash",
                "tt_bir_number": "TEST-BIR",
                "tt_nis_number": "TEST-NIS",
            }
        )
        cls.env["spx.tt.employee.pay.item"].create(
            {
                "employee_id": cls.employee.id,
                "pay_item_id": cls.phone_allowance.id,
                "amount": 250.0,
                "quantity": 1.0,
            }
        )

    def test_load_employee_and_build_initial_calculation(self):
        run = self.env["spx.tt.payroll.run"].create(
            {
                "company_id": self.env.company.id,
                "pay_frequency_id": self.monthly.id,
                "date_start": "2026-05-01",
                "date_end": "2026-05-31",
                "payment_date": "2026-05-31",
            }
        )
        run.action_load_employees()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        self.assertEqual(len(line), 1)
        self.assertEqual(line.gross_pay, 9750.0)
        self.assertEqual(line.total_deductions, 0.0)
        self.assertEqual(line.net_pay, 9750.0)
        self.assertTrue(line.item_line_ids.filtered(lambda item: item.source == "basic"))
        self.assertTrue(
            line.item_line_ids.filtered(
                lambda item: item.pay_item_id == self.phone_allowance
            )
        )

    def test_run_totals_exclude_held_employee(self):
        run = self.env["spx.tt.payroll.run"].create(
            {
                "company_id": self.env.company.id,
                "pay_frequency_id": self.monthly.id,
                "date_start": "2026-05-01",
                "date_end": "2026-05-31",
                "payment_date": "2026-05-31",
            }
        )
        run.action_load_employees()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        line.action_place_on_hold()
        self.assertEqual(run.net_pay, 0.0)
        self.assertEqual(run.held_count, 1)
    def test_employee_calculation_attendance_action(self):
        run = self.env["spx.tt.payroll.run"].create(
            {
                "company_id": self.env.company.id,
                "pay_frequency_id": self.monthly.id,
                "date_start": "2026-05-01",
                "date_end": "2026-05-31",
                "payment_date": "2026-05-31",
            }
        )
        run.action_load_employees()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        action = line.action_open_attendances()
        self.assertEqual(action["res_model"], "hr.attendance")
        self.assertIn(("employee_id", "=", self.employee.id), action["domain"])

