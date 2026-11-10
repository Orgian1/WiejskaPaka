"""Conservative deployment gate; never treats unit tests as proof of production readiness."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    postgres_integration_passed: bool = False
    rls_reviewed_and_tested: bool = False
    endpoint_authorization_reviewed: bool = False
    order_delivery_e2e_passed: bool = False
    financial_reconciliation_passed: bool = False
    legal_and_privacy_reviewed: bool = False
    payments_live_verified: bool = False
    production_infrastructure_verified: bool = False


REQUIREMENTS = {
    'postgres_integration_passed': 'Testy integracyjne na odizolowanym PostgreSQL',
    'rls_reviewed_and_tested': 'Zweryfikowana ochrona danych w PostgreSQL (RLS lub równoważna)',
    'endpoint_authorization_reviewed': 'Przegląd autoryzacji wszystkich endpointów',
    'order_delivery_e2e_passed': 'Test E2E zamówienie–dostawa–PIN–zwrot',
    'financial_reconciliation_passed': 'Uzgodnienie finansowe i testy współbieżności',
    'legal_and_privacy_reviewed': 'Przegląd prawny, konsumencki i prywatności',
    'payments_live_verified': 'Bezpieczna integracja operatora płatności i wypłat',
    'production_infrastructure_verified': 'Konfiguracja hostingu, sekretów, kopii i monitoringu',
}


def evaluate(evidence: Evidence) -> dict:
    pending = [description for field, description in REQUIREMENTS.items()
               if getattr(evidence, field) is not True]
    return {'production_ready': not pending, 'pending': pending,
            'verified': len(REQUIREMENTS) - len(pending), 'total': len(REQUIREMENTS)}


def default_report() -> dict:
    """Unknown external evidence is a failure, not an implicit pass."""
    return evaluate(Evidence())
