"""Read-only settlement planning; never initiates money movement."""
from dataclasses import asdict, dataclass
from backend.invoicing import calculate_commission_grosze

@dataclass(frozen=True)
class SettlementPreview:
    products_grosze: int
    delivery_grosze: int
    customer_total_grosze: int
    commission_grosze: int
    seller_amount_grosze: int
    commission_rate_basis_points: int
    currency: str = 'PLN'
    simulated: bool = True
    payout_scheduled: bool = False
    payment_captured: bool = False


def calculate(products_grosze: int, delivery_grosze: int, rate_basis_points: int) -> dict:
    if type(products_grosze) is not int or type(delivery_grosze) is not int:
        raise ValueError('Kwoty muszą być całkowitymi groszami')
    if not (0 <= products_grosze <= 9_000_000_000_000 and 0 <= delivery_grosze <= 9_000_000_000_000):
        raise ValueError('Kwota poza zakresem')
    if products_grosze + delivery_grosze > 9_000_000_000_000:
        raise ValueError('Suma poza zakresem')
    if type(rate_basis_points) is not int or not 0 <= rate_basis_points <= 10000:
        raise ValueError('Nieprawidłowa stawka prowizji')
    commission = calculate_commission_grosze(products_grosze, rate_basis_points)
    total = products_grosze + delivery_grosze
    seller = total - commission
    assert seller + commission == total
    return asdict(SettlementPreview(products_grosze, delivery_grosze, total, commission, seller, rate_basis_points))
