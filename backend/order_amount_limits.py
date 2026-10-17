"""Strict 64-bit database monetary bounds for test orders (integer grosze)."""
MAX_DB_INTEGER = 2**63 - 1


def checked_order_total(unit_price_grosze: int, quantity: int, delivery_grosze: int) -> tuple[int, int]:
    for value in (unit_price_grosze, quantity, delivery_grosze):
        if type(value) is not int or value < 0 or value > MAX_DB_INTEGER:
            raise ValueError('Nieprawidłowa wartość zamówienia')
    if unit_price_grosze < 1 or quantity < 1:
        raise ValueError('Cena i ilość muszą być dodatnie')
    if quantity > MAX_DB_INTEGER // unit_price_grosze:
        raise ValueError('Przekroczono dopuszczalną kwotę zamówienia')
    subtotal = unit_price_grosze * quantity
    if delivery_grosze > MAX_DB_INTEGER - subtotal:
        raise ValueError('Przekroczono dopuszczalną kwotę zamówienia')
    return subtotal, subtotal + delivery_grosze
