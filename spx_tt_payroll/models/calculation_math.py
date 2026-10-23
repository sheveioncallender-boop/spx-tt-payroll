"""Payroll arithmetic independent of the Odoo ORM.

Amounts are not rounded until they are written in the payroll currency.
Projection uses the current recurring taxable pay and recorded YTD history.
Manual one-off earnings are counted once, not projected into future pays.
"""
from datetime import date, timedelta


def mondays_between(start, end):
    if end < start:
        return 0
    first = start + timedelta(days=(7 - start.weekday()) % 7)
    return max(0, (end - first).days // 7 + 1)


def projection_periods(frequency, start, end, has_history):
    year_end = date(end.year, 12, 31)
    if frequency == "MONTHLY":
        return 13 - end.month, mondays_between(start, year_end)
    if frequency == "SEMI_MONTHLY":
        return (12 - end.month) * 2 + (2 if end.day <= 15 else 1), mondays_between(start, year_end)
    # Weekly first pay with no history is treated as a typical annual week.
    weeks = mondays_between(start if has_history else date(end.year, 1, 1), year_end)
    weeks = max(1, weeks)
    return (weeks / 2.0 if frequency == "FORTNIGHTLY" else weeks), weeks


def projected_paye(*, taxable, one_off, weekly_nis, frequency, start, end,
                   previous_taxable=0.0, previous_nis=0.0, previous_paye=0.0,
                   previous_periods=0, personal_allowance=90000.0,
                   pension=0.0, other_deductions=0.0, credits=0.0):
    periods, weeks = projection_periods(frequency, start, end, bool(previous_periods))
    periods = max(1.0, periods)
    annual_gross = previous_taxable + taxable + (taxable - one_off) * (periods - 1)
    annual_nis = previous_nis + max(0.0, weekly_nis) * weeks
    relief = min(60000.0, max(0.0, pension) + annual_nis * 0.7)
    chargeable = max(0.0, annual_gross - personal_allowance - relief - other_deductions)
    tax = min(chargeable, 1000000.0) * 0.25 + max(0.0, chargeable - 1000000.0) * 0.30
    amount = max(0.0, (tax - credits - previous_paye) / periods)
    return dict(amount=amount, annual_gross=annual_gross, annual_nis=annual_nis,
                relief=relief, chargeable=chargeable, periods=periods)


def td1_is_current(profile, payment_date):
    return bool(profile and profile.td1_approved
                and (not profile.td1_effective_date or profile.td1_effective_date <= payment_date)
                and (not profile.td1_expiry_date or profile.td1_expiry_date >= payment_date))
