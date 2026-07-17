{
    "name": "Trinidad & Tobago Payroll",
    "version": "19.0.1.3.1",
    "summary": "Automatic employee loading, 160-hour monthly payroll periods, and payslip-aligned sections",
    "description": """
Phase 2B refinement of the Trinidad & Tobago Payroll suite.

Uses Odoo Employees and Odoo Attendances directly. Payroll runs automatically
load matching employees automatically when a payroll run is created, snapshot
attendance, calculate Salary or Regular Hours from payroll-standard expected hours,
pull recurring additions and deductions, and organize PAYE, NIS, Health Surcharge,
and other items into payslip-aligned sections ready for the statutory phase. It remains independent of Accounting and any localization.
    """,
    "category": "Human Resources/Payroll",
    "author": "Spxcorp Limited",
    "maintainer": "Spxcorp Limited",
    "website": "https://www.spxcorp.net",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "hr_attendance",
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
        "views/payroll_run_views.xml",
        "views/hr_employee_views.xml",
        "wizard/payroll_readiness_views.xml",
        "views/res_config_settings_views.xml",
        "views/payroll_menus.xml",
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
