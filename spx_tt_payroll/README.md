# Trinidad & Tobago Payroll — Phase 2B Structure

Version 19.0.1.3.0 for Odoo 19 Community and Enterprise.

## Included

- Existing Odoo Employees remain the employee source.
- Simple Salaried or Hourly Paid basis, separate from pay frequency.
- Salary or hourly rate stored on the TT Payroll employee workspace.
- Generate Payroll loads matching employees automatically.
- Odoo Attendance check-ins/check-outs are snapshotted for the selected period.
- Expected, clocked, regular, overtime, leave, public-holiday, payable, and unpaid hours.
- Salaried employees are prorated from payable hours.
- Hourly employees are calculated from payable hours and hourly rate.
- Recurring additions/deductions can be set to Auto Add and limited by pay frequency.
- PAYE, Employee NIS, Health Surcharge, and Employer NIS lines are always created.
- Statutory lines remain at zero/manual until the verified Trinidad tables are added.
- No Accounting or localization dependency.

## Normal flow

Create Payroll Run → Generate Payroll → Review Attendance & Hours → Recalculate Earnings → Confirm Attendance → Review → Approve.

## Important

This is the calculation structure phase. PAYE, NIS, Health Surcharge, public-holiday and overtime rules must be verified and completed in the next statutory/rules phase before production payroll use.


## v1.3.1 refinements
- New payroll runs automatically load eligible employees on save.
- Monthly expected hours use four payroll weeks (40 hours/week = 160 hours/month).
- Legacy duplicate Basic Pay/Salary lines are normalized in open runs.
- Payroll items are presented as Wages, Additions, Taxes, Deductions, Loans, and Employer Contributions.


## Version 1.3.2

- Salary is always prorated from final payable hours.
- Zero payable hours produces zero Salary.
- Approved Hours Adjustment recalculates pay automatically.
- Attendance refresh rebuilds the Salary line from the refreshed snapshot.
- Recurring employee items cannot duplicate Salary or attendance-generated wages.
