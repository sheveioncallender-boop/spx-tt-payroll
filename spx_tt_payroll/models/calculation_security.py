"""Private capabilities cannot be supplied as booleans through RPC context."""
INTERNAL = object()
WORKFLOW = object()
LOCKED = ("approved", "paid", "cancelled")


def internal(record):
    return record.env.context.get("tt_payroll_internal_write") is INTERNAL


def workflow(record):
    return record.env.context.get("tt_payroll_workflow") is WORKFLOW
