{
    "name": "Trinidad & Tobago Payroll",
    "version": "19.0.1.0.3",
    "summary": "Simple Trinidad and Tobago payroll foundation for Odoo Employees and Attendances",
    "description": """
Phase 1 of the Trinidad & Tobago Payroll suite.

Provides the payroll foundation, employee payroll profiles, pay frequencies,
payroll groups, recurring earnings and deductions, access roles, company
defaults, and a payroll readiness review. It is intentionally independent of
Accounting and any accounting localization.
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
        "views/payroll_group_views.xml",
        "views/pay_item_views.xml",
        "views/employee_pay_item_views.xml",
        "views/hr_employee_views.xml",
        "wizard/payroll_readiness_views.xml",
        "views/res_config_settings_views.xml",
        "views/payroll_menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "application": True,
    "installable": True,
    "auto_install": False,
}
