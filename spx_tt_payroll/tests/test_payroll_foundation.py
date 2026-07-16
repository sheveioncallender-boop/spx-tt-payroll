from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestTTPayrollFoundation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.monthly = cls.env.ref("spx_tt_payroll.pay_frequency_monthly")
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Payroll Test Employee",
                "company_id": cls.env.company.id,
                "resource_calendar_id": cls.env.company.resource_calendar_id.id,
                "tt_pay_type": "monthly",
                "tt_pay_frequency_id": cls.monthly.id,
                "tt_monthly_salary": 6000.0,
                "tt_bir_number": "1000000000",
                "tt_nis_number": "100000000",
                "tt_payment_method": "cash",
                "tt_normal_hours_per_day": 8.0,
                "tt_normal_hours_per_week": 40.0,
            }
        )

    def test_normal_odoo_employee_is_used_by_payroll(self):
        self.assertEqual(self.employee._name, "hr.employee")
        self.assertEqual(self.employee.tt_payroll_status, "active")
        self.assertEqual(self.employee.tt_payroll_readiness_state, "ready")

    def test_employee_readiness(self):
        self.assertEqual(self.employee.tt_payroll_readiness_state, "ready")
        self.employee.tt_bir_number = False
        self.assertEqual(self.employee.tt_payroll_readiness_state, "incomplete")
        self.assertIn("BIR", self.employee.tt_payroll_issue_summary)

    def test_excluded_employee_is_not_required_for_payroll(self):
        self.employee.tt_payroll_status = "excluded"
        self.assertEqual(self.employee.tt_payroll_readiness_state, "not_enrolled")
        self.assertEqual(self.employee.tt_payroll_issue_count, 0)

    def test_negative_rate_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.employee.tt_monthly_salary = -1.0

    def test_new_employee_uses_company_defaults(self):
        self.env.company.tt_payroll_default_frequency_id = self.monthly
        self.env.company.tt_payroll_default_hours_per_day = 7.5
        self.env.company.tt_payroll_default_hours_per_week = 37.5
        employee = self.env["hr.employee"].create(
            {
                "name": "Default Payroll Employee",
                "company_id": self.env.company.id,
            }
        )
        self.assertEqual(employee.tt_pay_frequency_id, self.monthly)
        self.assertEqual(employee.tt_normal_hours_per_day, 7.5)
        self.assertEqual(employee.tt_normal_hours_per_week, 37.5)

    def test_attendance_button_uses_odoo_attendance(self):
        action = self.employee.action_tt_open_attendances()
        self.assertEqual(action["res_model"], "hr.attendance")
        self.assertIn(("employee_id", "=", self.employee.id), action["domain"])

    def test_employee_number_is_generated(self):
        self.assertTrue(self.employee.tt_employee_number)

    def test_current_pay_summary(self):
        self.assertEqual(self.employee.tt_current_pay_amount, 6000.0)
        self.assertEqual(self.employee.tt_current_pay_unit, "per month")

    def test_payroll_profile_uses_same_employee(self):
        action = self.employee.action_tt_open_payroll_profile()
        self.assertEqual(action["res_model"], "hr.employee")
        self.assertEqual(action["res_id"], self.employee.id)
