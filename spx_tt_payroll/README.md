# Trinidad & Tobago Payroll — Phase 1

Version: **19.0.1.0.5**

This is the first stable foundation for the Trinidad & Tobago Payroll suite for
Odoo 19 Community and Enterprise.

## Core design

Payroll does not create a separate employee database.

- Every employee remains an Odoo `hr.employee` record.
- The module adds a Payroll tab to the normal Odoo Employee form.
- Every active Odoo employee is available to payroll automatically.
- Set Payroll Status to **Excluded** only when an employee must not be paid.
- Work schedules come from the employee's standard Odoo Working Hours field.
- Check-ins, check-outs, worked hours, and overtime remain in Odoo Attendances.
- Payroll will read and validate those standard attendance records in Phase 2.

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
- Direct links to Odoo Employees and Odoo Attendances.
- Payroll filters and optional payroll columns on Odoo's normal Employees screen.

## Important architecture

- Independent from Accounting and all accounting localizations.
- Uses Odoo Employees and Odoo Attendances directly.
- Does not duplicate employee or attendance records.
- Does not depend on Odoo Enterprise Payroll, so the same core module can be
  installed in Community or Enterprise.
- Accounting mappings and journal posting will be provided as an optional later
  component.

## Installation or upgrade

1. Replace the existing `spx_tt_payroll` folder with this version.
2. Restart Odoo.
3. Enable developer mode and update the Apps list.
4. Install or upgrade **Trinidad & Tobago Payroll**.
5. Open the normal Odoo Employees app and select an employee.
6. Complete the employee's Payroll tab.

## Normal user flow in Phase 1

1. Open **Trinidad Payroll → Employees**. This opens Odoo's standard Employees.
2. Open an existing employee and select the **Payroll** tab.
3. Enter the employee's pay, statutory, and payment information.
4. Confirm the employee's Odoo Work Schedule and Attendance Approver.
5. Use **Open Odoo Attendances** to view the employee's standard attendance data.
6. Open **Payroll Readiness** to see anything still missing.
7. Set Payroll Status to **Excluded** only for employees who must not be included.

## Version 1.0.5

- Removed the separate Payroll Employees experience.
- Payroll now opens and extends Odoo's standard Employees screen.
- All active Odoo employees are considered by payroll automatically unless excluded.
- Added payroll filters and optional columns to the standard Employees views.
- Added the Odoo Work Schedule, Attendance Approver, and Overtime Ruleset to the
  Payroll tab for convenience.
- Added a direct link to the employee's records in Odoo Attendances.
- Payroll Officers now receive the Odoo Attendance Officer access needed for the
  attendance review phase.
- Readiness drill-downs now open Odoo's standard Employee list and form views.

## Next phase

Phase 2 will read Odoo Attendance records, compare actual time with work
schedules, identify missing punches and unusual attendance, and provide a simple
attendance approval and payroll-hours freeze. It will not create a replacement
attendance system.
