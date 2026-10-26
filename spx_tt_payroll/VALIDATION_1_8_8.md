# TT Payroll v1.8.8 — attendance review clarity

Odoo module version: **19.0.1.8.8**. Install branch: **main**.

This maintenance update preserves the v1.8.7 calculation fixes and existing
native Odoo Attendance and Time Off workflows.

- Acknowledging attendance with a review note no longer displays **Ready**
  while a missing check-out, pending approval, or attendance/leave conflict
  remains. The existing review and payroll approval checks still apply.
- Accepted unpaid shortages can still be acknowledged and reviewed using the
  existing note workflow.
- Attendance adjustment buttons and review summaries occupy complete form
  rows, keeping labels and values aligned in Odoo's native form layout.

The regression suite covers conflicting approved leave after acknowledgement
and the accepted-shortage workflow. No statutory formulas are changed.

Update the deployment from `main`, restart/rebuild through the hosting service,
and upgrade the existing **Trinidad & Tobago Payroll** app in Odoo. Do not
uninstall it. Refresh the browser after the upgrade. Verify the Attendance &
Hours layout and status on the target Enterprise instance.

Phase 6 and the broader dashboard redesign remain separate work. This update
does not constitute final statutory or production acceptance.
