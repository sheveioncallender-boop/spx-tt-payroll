# TT Payroll v1.8.7 — Enterprise audit corrections

Odoo module version: **19.0.1.8.7**. Install branch: **main**.

This update continues v1.8.6. It fixes attendance/leave overlap, per-clocking
overtime allocation, refused-overtime status, stale shortage messages, native
Attendance navigation, Unicode payslip report wrapping and misleading dashboard
figures. It does not introduce Phase 6 or change native Odoo timekeeping.

The detailed Enterprise audit is supplied privately, with observed results,
remaining checks and layout recommendations.
The statutory reference cases and projection explanation remain in
[the v1.8.6 validation report](VALIDATION_1_8_6.md).

## Install on the Cloudpepper test instance

1. Update the existing deployment from `sheveioncallender-boop/spx-tt-payroll`,
   branch `main`, and restart/rebuild the Odoo service using Cloudpepper's normal
   deployment controls.
2. Upgrade the installed **Trinidad & Tobago Payroll** app in Odoo. Do not
   uninstall it, create a second employee system, or install an accounting
   localization for this update.
3. Confirm the installed module version is `19.0.1.8.7`. Reload the browser to
   pick up updated views/assets.
4. Repeat the targeted Enterprise checks in the private audit report. Preserve
   the approved QA run as the before/after history check; use a separate draft
   fixture for new calculation tests.

No real payroll should be processed solely on the basis of this audit. Final
statutory acceptance and the listed deployment tests remain outstanding.
