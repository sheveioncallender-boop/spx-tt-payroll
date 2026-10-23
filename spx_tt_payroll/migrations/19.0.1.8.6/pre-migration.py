"""Do not silently retain duplicates when adding Odoo 19 constraints."""


def migrate(cr, version):
    checks = [
        ("spx_tt_payroll_run_employee", "run_id, employee_id"),
        ("spx_tt_employee_statutory_profile", "employee_id"),
        ("spx_tt_pay_frequency", "code"),
        ("spx_tt_pay_item", "code, company_id"),
        ("spx_tt_payroll_group", "code, company_id"),
    ]
    for table, keys in checks:
        # All identifiers above are fixed developer-owned names, never user input.
        cr.execute(f"SELECT array_agg(id ORDER BY id) FROM {table} GROUP BY {keys} HAVING count(*) > 1 LIMIT 5")
        duplicates = cr.fetchall()
        if duplicates:
            raise RuntimeError(
                f"TT Payroll upgrade stopped: duplicate records in {table}: {duplicates}. "
                "Resolve duplicates on a test copy before upgrading. No records have been merged or deleted."
            )
