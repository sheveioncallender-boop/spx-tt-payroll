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

    def test_current_pay_is_nonstored_helper(self):
        self.assertEqual(self.employee.tt_current_pay_amount, 6000.0)
        self.assertEqual(self.employee.tt_current_pay_unit, "per month")
        self.assertFalse(self.employee._fields["tt_current_pay_amount"].store)

    def test_employee_number_alias_uses_attendance_barcode(self):
        self.employee.tt_employee_number = "CLOCK-001"
        self.assertEqual(self.employee.barcode, "CLOCK-001")
