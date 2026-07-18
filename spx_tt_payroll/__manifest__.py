{
    "name": "Trinidad & Tobago Payroll",
    "version": "19.0.1.7.1",
    "summary": "Premium Trinidad & Tobago payroll payslips with current and YTD summaries",
    "description": """
Phase 7 premium payslip reporting for Trinidad & Tobago Payroll.

Uses Odoo Employees and Attendances directly, prorates Salary or Regular Hours
from final payable hours, automatically loads recurring additions and deductions,
and now calculates PAYE, Employee NIS, Employer NIS, and Health Surcharge.
The 2026 NIBTT earnings classes are built in, PAYE supports personal allowance,
TD1 deductions and credits, and earnings are taxable by default unless excluded.
Manual payable-hours changes now require a reason in a dedicated window,
immediately recalculate wages and statutory deductions, and create permanent
before-and-after audit history. Calculation status now opens a guided list of
unresolved items with direct actions to fix attendance, employee setup, and pay.
Approved Odoo Time Off is now pulled into payroll as a permanent paid/unpaid
leave snapshot, pending requests are flagged, and attendance/time-off conflicts
are prevented from being paid twice. A premium payslip now follows the established Trinidad payroll structure with Wages, Bank Transfers, Additions, Taxes, Deductions, Loans, and Current/YTD totals. Accounting remains optional and independent of the Trinidad accounting localization.
    """,
    "category": "Human Resources/Payroll",
    "author": "Spxcorp Limited",
    "maintainer": "Spxcorp Limited",
    "website": "https://www.spxcorp.net",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "hr_attendance",
        "hr_holidays",
        "mail",
    ],
    "data": [
        "security/payroll_security.xml",
        "security/ir.model.access.csv",
        "data/pay_frequency_data.xml",
        "data/pay_item_data.xml",
        "data/payroll_run_sequence.xml",
        "views/payroll_group_views.xml",
        "views/pay_item_views.xml",
        "views/employee_pay_item_views.xml",
        "views/employee_statutory_profile_views.xml",
        "views/time_off_snapshot_views.xml",
        "wizard/payroll_hours_adjustment_views.xml",
        "wizard/payroll_attention_views.xml",
        "views/payroll_run_views.xml",
        "views/hr_employee_views.xml",
        "wizard/payroll_readiness_views.xml",
        "views/res_config_settings_views.xml",
        "views/payroll_menus.xml",
        "reports/payslip_templates.xml",
        "reports/payslip_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "spx_tt_payroll/static/src/css/tt_payroll_employee.css",
        ],
    },
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
    "auto_install": False,
}
