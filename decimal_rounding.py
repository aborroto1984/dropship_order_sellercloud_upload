from decimal import Decimal, ROUND_HALF_UP


def round_to_decimal(number):
    """Round a number to a given precision."""
    decimal_number = Decimal(str(number))
    rounded_number = decimal_number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return float(rounded_number)
