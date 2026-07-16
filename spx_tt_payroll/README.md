# Trinidad & Tobago Payroll — Employee Workspace

Version: **19.0.1.1.0**

This build begins the refined Trinidad & Tobago payroll approach for Odoo 19
Community and Enterprise.

## Core design

The module does not create a second employee database.

- Every payroll employee is the same Odoo `hr.employee` record.
- The Trinidad Payroll menu opens a dedicated payroll-focused employee workspace.
- Standard Odoo information such as name, photo, job, department, manager,
  contact details, work schedule, badge ID, and bank accounts is reused.
- The module adds only information needed for Trinidad payroll.
- Odoo Attendances remains the source of check-ins and check-outs.
- Accounting remains optional and is not required by this module.

## Employee workspace

The modern TT Payroll Employee screen includes:

- Employee photo and identity header
- Payroll status and setup status
- Base pay, frequency, group, and payment summary
- Employment and organization information
- Personal and contact information from Odoo Employees
- Monthly, weekly, daily, and hourly pay setup
- BIR, NIS, Health Surcharge, and TD1 information
- Separate recurring Earnings and Deductions tabs
- Deduction references and balances for future loan processing
- Standard Odoo employee bank accounts
- Attendance badge/PIN, work schedule, and overtime rules
- Internal payroll notes
- Direct buttons for Attendances and the full Odoo Employee record

## Employee Setup

The old Payroll Checklist menu is replaced by **Employee Setup**.

It opens a normal Odoo employee list filtered to employees who need attention.
The list clearly shows each employee's payroll status, base pay, frequency,
payment method, setup status, and number of missing items.

## Installation or upgrade

1. Replace the existing `spx_tt_payroll` folder with this version.
2. Restart Odoo.
3. Update the Apps list.
4. Upgrade **Trinidad & Tobago Payroll**.
5. Hard-refresh the browser after the upgrade.
6. Open **Trinidad Payroll → Employees**.

## Next build stage

The next stage will create the Payroll Run workspace: payroll periods, employee
selection, editable earnings and deductions, attendance summaries, Trinidad
statutory calculations, current and year-to-date totals, and a live payslip
preview.
