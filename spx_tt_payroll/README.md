# Trinidad & Tobago Payroll — Phase 1

Version: **19.0.1.0.0**

This is the first stable foundation for the Trinidad & Tobago Payroll suite for
Odoo 19 Community and Enterprise.

## What Phase 1 includes

- A Payroll tab on Odoo Employee records.
- Monthly, weekly, daily, and hourly pay details.
- Weekly, fortnightly, semi-monthly, monthly, and off-cycle frequencies.
- Payroll groups for employees who share pay frequency and normal working hours.
- BIR, NIS, Health Surcharge exemption, and payment information.
- Recurring earnings and deductions.
- Standard Trinidad payroll earning and deduction types.
- Payroll User, Officer, Reviewer, and Manager access roles.
- A payroll readiness review showing missing information in plain language.
- Company defaults that remain editable at any time.

## Important architecture

- Independent from Accounting and all accounting localizations.
- Uses Odoo Employees and is ready for the Attendance integration in Phase 2.
- Does not depend on Odoo Enterprise Payroll, so the same core module can be
  installed in Community or Enterprise.
- Accounting mappings and journal posting will be provided as an optional later
  component.

## Installation

1. Copy the `spx_tt_payroll` folder into the Odoo custom add-ons directory.
2. Restart Odoo.
3. Enable developer mode and update the Apps list.
4. Install **Trinidad & Tobago Payroll**.
5. Assign users a Trinidad Payroll role under user access rights.

## Normal user flow in Phase 1

1. Open **Trinidad Payroll → Employees**.
2. Open an employee and select the **Payroll** tab.
3. Turn on **Include in Trinidad Payroll**.
4. Enter the employee's pay, statutory, and payment information.
5. Open **Payroll Readiness** to see anything still missing.

## Next phase

Phase 2 will pull Odoo Attendance records, compare actual time with work
schedules, identify missing punches and unusual attendance, and provide a simple
attendance approval and payroll-hours freeze.

## 19.0.1.0.1 installation fix

- Removed schema-time defaults that queried custom company columns before those columns existed.
- Updated access groups to Odoo 19's `res.groups.privilege` structure.
- Automatically grants the standard Odoo administrator Payroll Manager access after installation.
