"""Independent PAYE fixtures for first and later pays; no Odoo dependency."""
import importlib.util
from pathlib import Path
from datetime import date
import unittest
spec=importlib.util.spec_from_file_location("math_rules",Path(__file__).resolve().parents[1]/"spx_tt_payroll/models/calculation_math.py")
math_rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(math_rules)

class ProjectionTests(unittest.TestCase):
    def calculate(self, **changes):
        values=dict(taxable=9500,one_off=0,weekly_nis=122,frequency="MONTHLY",start=date(2026,1,1),end=date(2026,1,31))
        values.update(changes)
        return math_rules.projected_paye(**values)

    def test_first_month_matches_calculator(self):
        self.assertAlmostEqual(self.calculate()["amount"],407.4833333333,places=7)

    def test_february_accounts_for_prior_tax_and_nis(self):
        result=self.calculate(start=date(2026,2,1),end=date(2026,2,28),previous_taxable=9500,
                              previous_nis=488,previous_paye=407.48,previous_periods=1)
        self.assertAlmostEqual(result["annual_gross"],114000)
        self.assertAlmostEqual(result["annual_nis"],6344)
        self.assertAlmostEqual(result["amount"],407.4836363636,places=7)

    def test_five_monday_june_with_history(self):
        result=self.calculate(start=date(2026,6,1),end=date(2026,6,30),previous_taxable=47500,
                              previous_nis=2562,previous_paye=2037.4,previous_periods=5)
        self.assertAlmostEqual(result["amount"],407.4857142857,places=7)

    def test_late_first_month_does_not_invent_previous_pay(self):
        self.assertEqual(self.calculate(start=date(2026,5,1),end=date(2026,5,31))["amount"],0)

    def test_one_off_bonus_not_repeated_twelve_times(self):
        result=self.calculate(taxable=10500,one_off=1000)
        self.assertEqual(result["annual_gross"],115000)
        self.assertAlmostEqual(result["amount"],428.3166666667,places=7)

    def test_december_settles_remaining_projected_tax(self):
        result=self.calculate(start=date(2026,12,1),end=date(2026,12,31),previous_taxable=104500,
                              previous_nis=5856,previous_paye=4482.28,previous_periods=11)
        self.assertAlmostEqual(result["amount"],407.52,places=7)

    def test_overpaid_tax_does_not_create_an_unapproved_refund(self):
        self.assertEqual(self.calculate(previous_paye=10000,previous_periods=1)["amount"],0)

    def test_weekly_first_pay_matches_calculator(self):
        result=self.calculate(taxable=2000,weekly_nis=109.4,frequency="WEEKLY",
                              start=date(2026,1,5),end=date(2026,1,11))
        self.assertAlmostEqual(result["amount"],48.1626923077,places=7)

    def test_weekly_with_history(self):
        result=self.calculate(taxable=2000,weekly_nis=109.4,frequency="WEEKLY",
                              start=date(2026,1,12),end=date(2026,1,18),previous_periods=1,
                              previous_taxable=2000,previous_nis=109.4,previous_paye=48.16)
        self.assertEqual(result["annual_gross"],104000)
        self.assertAlmostEqual(result["amount"],48.1627450980,places=7)

    def test_semimonthly_projection(self):
        result=self.calculate(taxable=4750,frequency="SEMI_MONTHLY",end=date(2026,1,15))
        self.assertEqual(result["periods"],24)
        self.assertAlmostEqual(result["amount"],203.7416666667,places=7)

    def test_fortnightly_projection(self):
        result=self.calculate(taxable=4000,weekly_nis=109.4,frequency="FORTNIGHTLY")
        self.assertEqual(result["periods"],26)
        self.assertAlmostEqual(result["amount"],96.3253846154,places=7)

    def test_53_monday_year(self):
        self.assertEqual(math_rules.mondays_between(date(2029,1,1),date(2029,12,31)),53)

if __name__=="__main__":unittest.main()
