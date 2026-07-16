# Trinidad & Tobago Payroll — Phase 2A v1.2.0

Payroll employee setup and payroll run foundation for Odoo 19 Community and Enterprise.

## Phase 2A adds

- Payroll Runs with weekly, fortnightly, semi-monthly, monthly, and off-cycle frequencies.
- Period start/end dates, pay date, payroll year, calendar-day count, Monday count, and payroll-week count.
- Automatic loading of eligible Odoo employees by company, pay frequency, payroll group, and department.
- One employee calculation record per payroll run.
- Automatic Basic Pay and recurring employee earnings/deductions.
- Editable rate, quantity, factor, manual amount, and total lines.
- Gross pay, total deductions, employer contributions, and net pay.
- Employee calculation status: Ready, Needs Attention, Reviewed, On Hold, or Excluded.
- Draft, Attendance Review, Calculated, Under Review, Approved, and Paid workflow.
- Locking of approved and paid calculations.

## Important scope

This release provides the payroll run workspace and basic calculation foundation.
Full Odoo Attendance/Time Off collection and Trinidad PAYE, NIS, and Health Surcharge
calculations are added in the next phases.

The module remains independent of Accounting and any accounting localization.
