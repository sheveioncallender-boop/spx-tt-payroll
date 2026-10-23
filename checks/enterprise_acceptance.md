# Enterprise acceptance testing — 23 October 2026

Work in progress; not a production sign-off. Phase 6 remains paused.

## Live test fixtures

Synthetic employee `QA TT Payroll — Monthly 9500`, native employee ID 2;
salary 9,500, monthly, normal 40 hours/week, cash, synthetic BIR/NIS identifiers.
Native employment start set to 1 January 2026. QA run `TT/PR/2026/00001`
contains this employee; existing Administrator is excluded from this run only.
Company currency corrected from USD to TTD through native company settings.
No real payments or accounting postings are made.

## Observed passes

- Payroll and native employee workspace open on Enterprise.
- Twenty native January attendance records, including scheduled lunch breaks.
- Generate Payroll automatically loads employee and 159 worked hours.
- 159/160 salary = 9,440.63; deductions 913.64; net 8,526.99.
- Mandatory hours-adjustment reason blocks an empty reason.
- Audited -19 adjustment gives 140 payable hours, salary 8,312.50,
  deductions 590.76, net 7,721.74; clocked hours stay 159.
- Zero payable hours gives zero salary, deductions and net.
- Above-normal hours cap payable salary at 9,500.
- January full salary: PAYE 407.48; employee NIS 488; employer NIS 976;
  Health Surcharge 33; net 8,571.52.
- Reviewing unconfirmed attendance is blocked.
- Confirming a short-pay period requires a review note; accepted note permits
  Ready then Reviewed.
- Native checkout corrected from 16:00 to 17:00; refresh pulls 160 hours,
  recalculates salary to 9,500, clears attendance confirmation and review.
- 500 taxable bonus increases gross to 10,000, PAYE to 532.48, net to 8,946.52.
- Exclude from PAYE keeps gross 10,000 and returns PAYE to 407.48;
  net 9,071.52. NIS/HS unchanged for the configured bonus item.
- 100 other deduction gives net 8,971.52.
- Pending native Unpaid leave on 7 January: snapshot 8 hours, no salary
  reduction, attention item generated.
- Draft PDF generated: one portrait Letter page, correct baseline figures,
  draft marker/watermark, salary hides internal hourly equivalent.

## Findings to investigate/fix

1. PDF corrupts non-ASCII employee name: em dash printed as `â€”`.
2. Summary pay basis/frequency/payable/expected fields look editable although
   server guards protect snapshots. Automatic wage/statutory rows expose edit,
   add/delete controls that conflict with server protections.
3. Attendance shortcut on Enterprise opens today's Gantt despite a January
   payroll; use native list first or anchor the native calendar to period.
4. Attendance issue summary remains the original shortage after an hours
   adjustment (says 1 hour while final missing is 20).
5. Approved unpaid leave overlapping attendance makes native Odoo classify
   that clocking as overtime. Payroll currently aggregates 9 overtime hours
   from an 8 worked-hour clocking, then subtracts the unpaid overlap again:
   143 regular + 9 overtime, gross 9,792.19 including 500 bonus. Conflict is
   flagged, but provisional calculations are misleading and require correction.
6. Refused overtime is inferred as pending from raw minus approved hours;
   investigate native overtime states and distinguish refused from pending.

## Remaining live checks

Paid leave, missing checkout, negative net, hourly/weekly and five-Monday
cases, recurring items, approval/locking/payslip history, role/company checks,
batch PDF, dashboard actions and visual comparison with native Accounting.
New code fixes will need deployment and live retest before Enterprise sign-off.
