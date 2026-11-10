"""Exact sales quantities. Money remains integer grosze; no binary floats.

This module is independent of storage. Integration must snapshot the unit and
price on each order and migrate stock/reservations together before enabling it.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Unit:
    label: str
    scale: int
    packaged: bool = False


UNITS = {
    'szt': Unit('szt.', 1),
    'kg': Unit('kg', 1000),
    'g': Unit('g', 1),
    'l': Unit('l', 1000),
    'ml': Unit('ml', 1),
    'opak': Unit('opak.', 1, True),
    'peczek': Unit('pęczek', 1),
    'sloik': Unit('słoik', 1, True),
    'butelka': Unit('butelka', 1, True),
    'worek': Unit('worek', 1, True),
    'skrzynka': Unit('skrzynka', 1, True),
    'tacka': Unit('tacka', 1, True),
}
MAX_QUANTITY_ATOMS = 1_000_000_000
MAX_PRICE_GROSZE = 100_000_000


def get_unit(code):
    if not isinstance(code, str) or code not in UNITS:
        raise ValueError('Nieznana jednostka sprzedaży')
    return UNITS[code]


def package_content(code, amount=None, content_unit=None):
    """Normalize declared content, e.g. one tray containing 250 g.

    A bottle/jar need not be sold as one litre/kilogram. Keep the sale unit
    separate from its declared content; never infer one from the other.
    """
    unit = get_unit(code)
    if amount is None and content_unit is None and not unit.packaged:
        return None
    if content_unit not in ('szt', 'kg', 'g', 'l', 'ml'):
        raise ValueError('Podaj zawartość opakowania w sztukach, masie lub objętości')
    atoms = quantity_atoms(amount, content_unit)
    return {'amount_atoms': atoms, 'unit': content_unit}


def quantity_atoms(text, code, *, allow_zero=False):
    """Accept decimal user input, reject exponents, floats and lost precision."""
    unit = get_unit(code)
    if not isinstance(text, str) or not 1 <= len(text) <= 32:
        raise ValueError('Podaj ilość jako tekst dziesiętny')
    import re
    value = text.strip().replace(',', '.')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,3})?', value):
        raise ValueError('Nieprawidłowa ilość')
    try:
        atoms = Decimal(value) * unit.scale
    except InvalidOperation as exc:
        raise ValueError('Nieprawidłowa ilość') from exc
    if atoms != atoms.to_integral_value():
        raise ValueError('Ilość jest zbyt dokładna dla tej jednostki')
    result = int(atoms)
    if not (0 if allow_zero else 1) <= result <= MAX_QUANTITY_ATOMS:
        raise ValueError('Ilość poza dozwolonym zakresem')
    return result


def quantity_text(atoms, code):
    unit = get_unit(code)
    if type(atoms) is not int or not 0 <= atoms <= MAX_QUANTITY_ATOMS:
        raise ValueError('Nieprawidłowa ilość bazowa')
    whole, remainder = divmod(atoms, unit.scale)
    return str(whole) if not remainder else f'{whole},{remainder:03d}'.rstrip('0')


def line_total_grosze(price_grosze, atoms, code):
    """Round one order line half-up, once, after multiplying exact quantity.

    Example: 201 grosze/kg * 0.5 kg = 101 grosze. Delivery is excluded and
    must still be charged once per shipment by the checkout policy.
    """
    unit = get_unit(code)
    if type(price_grosze) is not int or not 1 <= price_grosze <= MAX_PRICE_GROSZE:
        raise ValueError('Nieprawidłowa cena')
    if type(atoms) is not int or not 1 <= atoms <= MAX_QUANTITY_ATOMS:
        raise ValueError('Nieprawidłowa ilość bazowa')
    result = (price_grosze * atoms * 2 + unit.scale) // (2 * unit.scale)
    if result < 1:
        raise ValueError('Wartość pozycji musi wynosić co najmniej jeden grosz')
    return result
