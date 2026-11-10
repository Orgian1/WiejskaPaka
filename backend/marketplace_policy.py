"""Rozdzielenie sprzedaży rolnika od usługi platformy (bez wystawiania faktur)."""
from dataclasses import dataclass

@dataclass(frozen=True)
class SaleBreakdown:
    product_grosze: int
    delivery_grosze: int
    total_paid_grosze: int
    platform_commission_grosze: int
    seller_settlement_before_other_fees_grosze: int


def breakdown(product_grosze: int, delivery_grosze: int, commission_grosze: int) -> SaleBreakdown:
    """Rozliczenie informacyjne, nie dokument podatkowy ani dowód wypłaty."""
    for value in (product_grosze, delivery_grosze, commission_grosze):
        if type(value) is not int or not 0 <= value <= 9_000_000_000_000:
            raise ValueError('Kwoty muszą być nieujemnymi liczbami całkowitymi groszy')
    if commission_grosze > product_grosze:
        raise ValueError('Prowizja nie może przekroczyć wartości produktów')
    total = product_grosze + delivery_grosze
    if total > 9_000_000_000_000:
        raise ValueError('Przekroczono limit kwoty')
    seller = total - commission_grosze
    assert seller + commission_grosze == total
    return SaleBreakdown(product_grosze, delivery_grosze, total, commission_grosze, seller)


POLICY = {
    'marketplace_role': 'posrednik',
    'seller_of_products': 'rolnik_lub_inny_sprzedawca',
    'product_sale_document_issuer': 'sprzedawca_zgodnie_z_jego_statusem_podatkowym',
    'platform_document_scope': 'wlasna_usluga_prowizyjna',
    'payment_processing': 'planowana_integracja_operatora_platnosci',
    'product_invoices_issued_by_platform': False,
    'platform_invoices_issued_automatically': False,
    'real_payments_enabled': False,
    'ksef_connected': False,
    'notice': 'Dokumentowanie sprzedaży zależy od statusu sprzedawcy i nabywcy; szczególne zasady VAT RR dotyczą zakupów od rolnika ryczałtowego przez czynnego podatnika VAT.',
}
