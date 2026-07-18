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


## v1.4.3 PAYE earning treatment

- Salary, overtime, bonuses, and recurring allowances are included in PAYE taxable earnings by default.
- Use **Exclude from PAYE** only for an approved exception.
- Excluding an earning from PAYE does not remove it from Gross Pay, NIS treatment, Health Surcharge, or the payslip.


## Phase 4 - Controlled Payable Hours Adjustments

Payroll officers must use **Adjust Payable Hours** for manual attendance corrections.
Each adjustment requires hours to add/remove and a reason, recalculates wages and
statutory deductions immediately, posts a payroll chatter note, and saves immutable
before-and-after audit history. Direct editing of approved adjustment hours is blocked.

## v1.5.1 - Guided attention items

- Calculation Status now includes a **Review Items** action when issues remain.
- A guided window lists each unresolved issue in plain language.
- Each issue links directly to the appropriate resolution: employee profile,
  statutory details, Odoo Attendances, payable-hours adjustment, attendance
  confirmation, or payroll recalculation.
- Approved manual hours no longer leave the original no-attendance warning open;
  only the final attendance confirmation remains when the adjustment fully
  resolves expected hours.

## Phase 5A — Odoo Time Off integration (v1.6.0)

- Depends on Odoo Time Off (`hr_holidays`) and uses its employee requests, leave types, approval states, and paid/unpaid setting.
- Approved paid Time Off adds scheduled leave hours to payroll payable hours.
- Approved unpaid Time Off reduces payable hours and salary without requiring a duplicate payroll leave entry.
- Pending Time Off is displayed but never paid until it is approved in Odoo.
- A permanent payroll snapshot preserves the Time Off records used for each payroll calculation.
- Attendance that overlaps approved Time Off is flagged and prevented from being paid twice.
- Payroll officers can open the employee's original Odoo Time Off records directly from the calculation.
