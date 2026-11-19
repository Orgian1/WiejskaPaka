"""Pickup point subscription pricing (amounts are integer grosze)."""

POINT_MONTHLY_PRICE_GROSZE = 1000
POINT_BILLING_PERIOD_DAYS = 30


def amount_for_points(point_count: int) -> int:
    if not isinstance(point_count, int) or isinstance(point_count, bool) or point_count < 0:
        raise ValueError('Nieprawidłowa liczba punktów')
    return point_count * POINT_MONTHLY_PRICE_GROSZE
