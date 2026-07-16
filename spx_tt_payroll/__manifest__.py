{
    "name": "Trinidad & Tobago Payroll",
    "version": "19.0.1.2.0",
    "summary": "Trinidad payroll employee setup and payroll run workspace",
    "description": """
Phase 2A of the Trinidad & Tobago Payroll suite.

Extends Odoo Employees with Trinidad payroll fields, pay frequencies, payroll
groups, recurring earnings and deductions, access roles, company defaults,
a streamlined payroll employee workspace, and the first payroll run calculation workspace.
Odoo Attendances remains the single source of check-in, check-out, worked-hours, and overtime
records. It is intentionally independent of Accounting and any accounting localization.
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
