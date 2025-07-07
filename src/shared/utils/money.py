"""Utilidades para manejo de dinero."""
from decimal import Decimal, ROUND_HALF_UP
from typing import List


def format_currency(amount: Decimal, currency: str = "MXN") -> str:
    """Formatea una cantidad como moneda."""
    currency_symbols = {
        "MXN": "$",
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }

    symbol = currency_symbols.get(currency, currency)

    # Redondear a 2 decimales
    rounded_amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Formatear con comas para miles
    formatted = f"{rounded_amount:,.2f}"

    return f"{symbol}{formatted}"


def parse_currency_input(input_str: str) -> Decimal:
    """Convierte string de entrada a Decimal."""
    # Remover símbolos de moneda y espacios
    cleaned = input_str.replace("$", "").replace(",", "").replace(" ", "")

    try:
        return Decimal(cleaned)
    except (ValueError, TypeError):
        raise ValueError(f"No se puede convertir '{input_str}' a cantidad monetaria")


def round_money(amount: Decimal) -> Decimal:
    """Redondea cantidad a 2 decimales."""
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def sum_money_amounts(amounts: List[Decimal]) -> Decimal:
    """Suma una lista de cantidades monetarias."""
    return sum(amounts, Decimal('0'))


def calculate_percentage(amount: Decimal, percentage: Decimal) -> Decimal:
    """Calcula el porcentaje de una cantidad."""
    return round_money(amount * percentage / Decimal('100'))


def is_valid_amount(amount: Decimal) -> bool:
    """Valida si una cantidad es válida (positiva y con máximo 2 decimales)."""
    if amount < 0:
        return False

    # Verificar que tenga máximo 2 decimales
    decimal_places = len(str(amount).split('.')[-1]) if '.' in str(amount) else 0
    return decimal_places <= 2
