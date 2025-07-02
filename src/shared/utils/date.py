"""Utilidades para manejo de fechas."""
from datetime import date, datetime, timedelta
from typing import Tuple, List
import calendar


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """Obtiene el primer y último día de un mes."""
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


def get_week_range(target_date: date) -> Tuple[date, date]:
    """Obtiene el primer y último día de la semana."""
    days_since_monday = target_date.weekday()
    monday = target_date - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_year_range(year: int) -> Tuple[date, date]:
    """Obtiene el primer y último día del año."""
    first_day = date(year, 1, 1)
    last_day = date(year, 12, 31)
    return first_day, last_day


def get_previous_month(target_date: date) -> Tuple[int, int]:
    """Obtiene el año y mes anterior."""
    if target_date.month == 1:
        return target_date.year - 1, 12
    else:
        return target_date.year, target_date.month - 1


def get_next_month(target_date: date) -> Tuple[int, int]:
    """Obtiene el año y mes siguiente."""
    if target_date.month == 12:
        return target_date.year + 1, 1
    else:
        return target_date.year, target_date.month + 1


def get_months_between(start_date: date, end_date: date) -> List[Tuple[int, int]]:
    """Obtiene lista de (año, mes) entre dos fechas."""
    months = []
    current_date = start_date.replace(day=1)
    end_month = end_date.replace(day=1)

    while current_date <= end_month:
        months.append((current_date.year, current_date.month))
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    return months


def is_same_month(date1: date, date2: date) -> bool:
    """Verifica si dos fechas están en el mismo mes."""
    return date1.year == date2.year and date1.month == date2.month


def days_in_month(year: int, month: int) -> int:
    """Obtiene la cantidad de días en un mes."""
    return calendar.monthrange(year, month)[1]

