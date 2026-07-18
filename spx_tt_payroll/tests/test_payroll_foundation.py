from odoo.tests.common import TransactionCase


class TestTTPayrollFoundation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Payroll Test Employee",
                "tt_pay_type": "monthly",
                "tt_monthly_salary": 6000.0,
            }
        )

    def test_employee_uses_standard_odoo_record(self):
        self.assertEqual(self.employee._name, "hr.employee")

    def test_salary_alias_uses_existing_monthly_salary_column(self):
        self.assertEqual(self.employee.tt_pay_basis, "salary")
        self.assertEqual(self.employee.tt_salary, 6000.0)
        self.employee.tt_salary = 6250.0
        self.assertEqual(self.employee.tt_monthly_salary, 6250.0)
        self.assertFalse(self.employee._fields["tt_salary"].store)

    def test_current_pay_is_nonstored_helper(self):
        self.assertEqual(self.employee.tt_current_pay_amount, 6000.0)
        self.assertEqual(self.employee.tt_current_pay_unit, "monthly salary")
        self.assertFalse(self.employee._fields["tt_current_pay_amount"].store)

    def test_employee_number_alias_uses_attendance_barcode(self):
        self.employee.tt_employee_number = "CLOCK-001"
        self.assertEqual(self.employee.barcode, "CLOCK-001")

    def test_setup_status_is_live_and_searchable(self):
        self.employee.tt_payroll_status = "active"
        self.employee.tt_pay_frequency_id = False
        self.employee.tt_bir_number = False
        self.employee.tt_nis_number = False
        self.employee.tt_nis_exempt = False
        self.employee.tt_payment_method = "cash"
        self.employee.invalidate_recordset(
            ["tt_payroll_readiness_state", "tt_payroll_issue_count"]
        )
        self.assertEqual(
            self.employee.tt_payroll_readiness_state, "incomplete"
        )
        found = self.env["hr.employee"].search(
            [("tt_payroll_readiness_state", "=", "incomplete")]
        )
        self.assertIn(self.employee, found)

    def test_excluded_status_is_only_used_when_employee_is_excluded(self):
        self.employee.tt_payroll_status = "excluded"
        self.employee.invalidate_recordset(["tt_payroll_readiness_state"])
        self.assertEqual(
            self.employee.tt_payroll_readiness_state, "not_enrolled"
        )
