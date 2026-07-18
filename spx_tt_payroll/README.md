# Trinidad & Tobago Payroll for Odoo 19

Version 19.0.1.4.0 adds automatic statutory calculations to the attendance-first payroll workflow.

## Automatic statutory calculations

- PAYE using annualized/cumulative year-to-date earnings
- Resident personal allowance default of TT$90,000
- 25% tax up to TT$1,000,000 chargeable income and 30% above
- Employee TD1 deductions, pension/annuity relief, tax credits, and opening YTD values
- Employee and employer NIS using the NIBTT classes effective 5 January 2026
- Class Z employer-only NIS for employees under 16, aged 65+, or marked as receiving a retirement pension
- Health Surcharge at TT$8.25 or TT$4.80 per applicable payroll week, with age and pension-only exemptions

## Normal workflow

1. Create a payroll run.
2. Eligible Odoo employees and their attendance are loaded automatically.
3. Salary or Regular Hours is calculated from final payable hours.
4. Recurring additions and deductions are loaded from the employee profile.
5. PAYE, NIS, Employer NIS, and Health Surcharge are calculated automatically.
6. Review the Taxes and Employer Contributions tabs before approval.

Use **Employees > Statutory > PAYE / TD1 Settings** only for approved employee-specific deductions, tax credits, pension status, or opening year-to-date balances.

This module remains independent from Accounting and the Trinidad accounting localization.
