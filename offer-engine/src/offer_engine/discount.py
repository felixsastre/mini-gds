from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def discount_percent(spend: Decimal, max_percent: Decimal, constant: Decimal) -> Decimal:
    """Michaelis-Menten curve: max * spend / (constant + spend), rounded down to 2 decimals.

    Rounding down keeps the discount below the maximum for any spend.
    Raise ValueError for a negative spend, a maximum outside 0 to 100, or a constant of 0 or less.
    """
    if spend < 0:
        raise ValueError(f"spend cannot be negative: {spend}")
    if not 0 < max_percent <= 100:
        raise ValueError(f"the maximum discount must be above 0 and at most 100: {max_percent}")
    if constant <= 0:
        raise ValueError(f"the constant must be above 0: {constant}")
    return (max_percent * spend / (constant + spend)).quantize(CENTS, ROUND_DOWN)


def discounted_price(price: Decimal, percent: Decimal) -> Decimal:
    """The price after the discount; ValueError for a negative price or a bad percent."""
    if price < 0:
        raise ValueError(f"price cannot be negative: {price}")
    if not 0 <= percent <= 100:
        raise ValueError(f"a discount is 0 to 100 percent: {percent}")
    return (price * (100 - percent) / 100).quantize(CENTS, ROUND_HALF_UP)
