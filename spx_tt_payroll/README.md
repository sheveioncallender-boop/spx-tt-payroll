# Trinidad & Tobago Payroll — Phase 1 v1.1.1

Upgrade-safe TT Payroll employee workspace for Odoo 19 Community and Enterprise.

This build deliberately avoids adding new stored columns to `hr.employee` during
this visual workspace update. It uses the payroll fields created by Phase 1,
standard Odoo employee and attendance fields, and non-stored summary helpers.
This allows CloudPepper to start normally before the module upgrade is executed.

## Recovery from v1.1.0

1. Replace the v1.1.0 module folder with this folder.
2. Restart/redeploy Odoo. The web client should load because the missing
   `tt_employee_number` database column is no longer required.
3. Update the Apps list and upgrade Trinidad & Tobago Payroll.
4. Hard-refresh the browser.


## 19.0.1.1.2

- Restores deduction reference, original balance, remaining balance, and payslip visibility fields on recurring employee payroll items.
- Fixes the Odoo view validation error raised during upgrade from 19.0.1.1.1.
