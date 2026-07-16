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
                "tt_payroll_enabled": True,
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

    def test_employee_readiness(self):
        self.assertEqual(self.employee.tt_payroll_readiness_state, "ready")
        self.employee.tt_bir_number = False
        self.assertEqual(self.employee.tt_payroll_readiness_state, "incomplete")
        self.assertIn("BIR", self.employee.tt_payroll_issue_summary)

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
