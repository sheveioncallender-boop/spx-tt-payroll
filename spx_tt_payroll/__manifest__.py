{
    "name": "Trinidad & Tobago Payroll",
    "version": "19.0.1.8.5",
    "summary": "Attendance-first Trinidad & Tobago payroll with statutory calculations, employee processing, and professional payslips",
    "description": """
Trinidad & Tobago Payroll provides a complete, easy-to-use payroll workspace
for companies operating in Trinidad and Tobago.

The module works directly with Odoo Employees, Attendances, Work Schedules,
and Time Off. It automatically pulls employee attendance and approved leave
into payroll runs, calculates payable hours, prorates salaries, processes
recurring additions and deductions, and generates professional employee
payslips.

The system includes automatic Trinidad and Tobago statutory calculations for
PAYE, Employee NIS, Employer NIS, and Health Surcharge. Payroll officers can
review employee calculations, resolve attendance issues, apply controlled
payable-hours adjustments with reasons, and view payroll totals through a
modern interactive dashboard.

Key features include a dedicated TT Payroll employee workspace; salaried and
hourly-paid employees; weekly, fortnightly, semi-monthly, monthly, and off-cycle
payrolls; automatic employee loading; Odoo Attendance and Time Off integration;
attendance-based salary proration; paid and unpaid leave processing; recurring
earnings, allowances, deductions, and loans; guided payroll issues; permanent
audit history for payable-hours adjustments; current and year-to-date totals;
modern Trinidad and Tobago payslips; a live payroll dashboard; multi-company
support; and compatibility with Odoo 19 Community and Enterprise.

The module remains independent from Accounting and the Trinidad accounting
localization. Optional accounting integration can be added without making
payroll dependent on a specific chart of accounts or localization.

Created and developed by Spxcorp Limited.
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
        "wizard/payroll_dashboard_selector_views.xml",
        "views/payroll_run_views.xml",
        "views/hr_employee_views.xml",
        "wizard/payroll_readiness_views.xml",
        "views/res_config_settings_views.xml",
        "views/payroll_dashboard_views.xml",
        "views/payroll_menus.xml",
        "reports/payslip_templates.xml",
        "reports/payslip_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "spx_tt_payroll/static/src/css/tt_payroll_employee.css",
            "spx_tt_payroll/static/src/css/tt_payroll_dashboard.css",
        ],
    },
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
    "auto_install": False,
}
