from datetime import date, timedelta


def subtract_business_days(day: date, days: int) -> date:
    """`day` menos `days` días hábiles (lunes a viernes; no conoce los feriados)."""
    current = day
    remaining = days
    while remaining > 0:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current
