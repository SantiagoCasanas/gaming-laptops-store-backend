"""
Business-day arithmetic for Colombian operations.
v1: Monday-Friday only. Does not exclude Colombian public holidays.
v2 may integrate `workalendar` or a DB-backed holiday table.
"""
from datetime import date, timedelta


def add_business_days(start: date, days: int) -> date:
    """
    Return the date that is `days` business days (Mon-Fri) after `start`.
    Does NOT account for Colombian public holidays (v1).
    """
    if days <= 0:
        return start
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def business_days_between(start: date, end: date) -> int:
    """
    Count business days (Mon-Fri) between `start` (exclusive) and `end` (inclusive).
    Negative if end < start. Does NOT account for Colombian public holidays (v1).
    """
    if end == start:
        return 0
    step = 1 if end > start else -1
    count = 0
    current = start
    while current != end:
        current += timedelta(days=step)
        if current.weekday() < 5:
            count += step
    return count
