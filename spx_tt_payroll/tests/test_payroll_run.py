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
                "auto_include": True,
                "pay_frequency_ids": [(6, 0, [cls.monthly.id])],
            }
        )

    def _new_run(self):
        return self.env["spx.tt.payroll.run"].create(
            {
                "company_id": self.env.company.id,
                "pay_frequency_id": self.monthly.id,
                "date_start": "2026-05-01",
                "date_end": "2026-05-31",
                "payment_date": "2026-05-31",
            }
        )

    def test_load_employee_attendance_first_and_build_default_lines(self):
        run = self._new_run()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        self.assertEqual(len(line), 1)
        self.assertEqual(run.state, "draft")
        self.assertEqual(line.pay_basis, "salary")
        self.assertEqual(line.salary_amount, 9500.0)
        self.assertTrue(line.attendance_loaded_at)

        primary = line.item_line_ids.filtered(lambda item: item.source == "salary")
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary.pay_item_id, self.env.ref("spx_tt_payroll.pay_item_basic"))
        self.assertEqual(primary.description, "Salary")
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary.payslip_section, "wage")
        self.assertAlmostEqual(primary.amount, 0.0, places=2)
        self.assertAlmostEqual(line.payable_hours, 0.0, places=2)
        # The recurring telephone allowance remains payable, but Salary itself
        # must be zero when attendance and approved hours are zero.
        self.assertAlmostEqual(line.gross_pay, 250.0, places=2)
        self.assertTrue(
            line.item_line_ids.filtered(
                lambda item: item.pay_item_id == self.phone_allowance
                and item.source == "recurring"
            )
        )
        statutory_codes = set(
            line.item_line_ids.filtered(
                lambda item: item.source == "statutory"
            ).mapped("statutory_code")
        )
        self.assertEqual(
            statutory_codes,
            {"paye", "employee_nis", "health_surcharge", "employer_nis"},
        )
        tax_codes = set(line.tax_item_ids.mapped("statutory_code"))
        self.assertEqual(tax_codes, {"paye", "employee_nis", "health_surcharge"})

    def test_salary_prorates_from_final_payable_hours(self):
        run = self._new_run()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        self.assertEqual(line.scheduled_hours, 160.0)
        # This simulates an authorised correction after attendance review so the
        # employee receives the full period salary.
        line.attendance_adjustment_hours = line.scheduled_hours
        line.action_recalculate_earnings()
        salary_line = line.item_line_ids.filtered(lambda item: item.source == "salary")
        self.assertAlmostEqual(salary_line.amount, 9500.0, places=2)
        self.assertAlmostEqual(line.gross_pay, 9750.0, places=2)
        self.assertAlmostEqual(line.employee_nis_amount, 488.0, places=2)
        self.assertAlmostEqual(line.employer_nis_amount, 976.0, places=2)
        self.assertAlmostEqual(line.health_surcharge_amount, 33.0, places=2)
        self.assertEqual(line.nis_class_display, "Class XII")
        self.assertAlmostEqual(line.paye_amount, 469.98, places=2)
        self.assertAlmostEqual(line.net_pay, 8759.02, places=2)



    def test_td1_deductions_adjust_automatic_paye(self):
        self.env["spx.tt.employee.statutory.profile"].create(
            {
                "employee_id": self.employee.id,
                "td1_approved": True,
                "approved_other_deductions_annual": 2151.52,
            }
        )
        run = self._new_run()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        line.attendance_adjustment_hours = line.scheduled_hours
        line.action_recalculate_earnings()
        self.assertAlmostEqual(line.paye_amount, 425.16, places=2)
        self.assertAlmostEqual(line.employee_nis_amount, 488.0, places=2)
        self.assertAlmostEqual(line.health_surcharge_amount, 33.0, places=2)

    def test_recurring_salary_cannot_duplicate_system_salary(self):
        salary_item = self.env.ref("spx_tt_payroll.pay_item_basic")
        self.env["spx.tt.employee.pay.item"].create(
            {
                "employee_id": self.employee.id,
                "pay_item_id": salary_item.id,
                "amount": 9500.0,
                "quantity": 1.0,
                "auto_include": True,
            }
        )
        run = self._new_run()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        salary_lines = line.item_line_ids.filtered(
            lambda item: item.pay_item_id.code in ("BASIC", "REGULAR_HOURS")
        )
        self.assertEqual(len(salary_lines), 1)
        self.assertEqual(salary_lines.source, "salary")
        self.assertAlmostEqual(salary_lines.amount, 0.0, places=2)

    def test_run_totals_exclude_held_employee(self):
        run = self._new_run()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        line.action_place_on_hold()
        self.assertEqual(run.net_pay, 0.0)
        self.assertEqual(run.held_count, 1)

    def test_employee_calculation_attendance_action(self):
        run = self._new_run()
        line = run.employee_line_ids.filtered(
            lambda record: record.employee_id == self.employee
        )
        action = line.action_open_attendances()
        self.assertEqual(action["res_model"], "hr.attendance")
        self.assertIn(("employee_id", "=", self.employee.id), action["domain"])
