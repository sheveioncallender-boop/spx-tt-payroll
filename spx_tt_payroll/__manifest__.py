{
    "name": "Trinidad & Tobago Payroll",
    "version": "19.0.1.1.0",
    "summary": "Modern Trinidad and Tobago payroll employee workspace for Odoo 19",
    "description": """
Phase 1 of the Trinidad & Tobago Payroll suite.

Provides a dedicated TT Payroll employee workspace while continuing to use
Odoo's standard hr.employee records. It adds Trinidad payroll employment,
pay, statutory, recurring earning, recurring deduction, banking, and attendance
sections without creating a duplicate employee database. It remains independent
of Accounting and all accounting localizations.
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
        "data/employee_sequence_data.xml",
        "views/payroll_group_views.xml",
        "views/pay_item_views.xml",
        "views/employee_pay_item_views.xml",
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
