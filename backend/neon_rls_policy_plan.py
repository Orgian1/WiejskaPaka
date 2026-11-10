"""Review-only RLS policy blueprint; NEVER execute automatically.

These are SELECT-policy *candidates*, not a deployment migration. Existing
application writes, login, background jobs and admin workflows need separate
review before enabling RLS. A compromised shared SQL login can set custom GUCs.
"""
from .neon_identity import actor_id_sql

ACTOR = actor_id_sql()

SELECT_PREDICATES = {
    'users': f'id = ({ACTOR})',
    'sessions': f'user_id = ({ACTOR})',
    'orders': (
        f'(buyer_id = ({ACTOR}) OR farmer_id = ({ACTOR}) '
        'OR (fulfillment = \'dostawa\' AND status = \'w_drodze_testowo\' '
        'AND pin_used = 0 AND EXISTS ('
        'SELECT 1 FROM public.delivery_assignments da '
        f'WHERE da.order_id = orders.id AND da.courier_id = ({ACTOR}))))'
    ),
    'order_locations': (
        'EXISTS (SELECT 1 FROM public.orders o WHERE o.id = order_locations.order_id '
        f'AND (o.buyer_id = ({ACTOR}) OR '
        '(o.fulfillment = \'odbior\' AND o.farmer_id = '
        f'({ACTOR})) OR '
        '(o.fulfillment = \'dostawa\' AND o.status = \'w_drodze_testowo\' '
        'AND o.pin_used = 0 AND EXISTS ('
        'SELECT 1 FROM public.delivery_assignments da '
        f'WHERE da.order_id = o.id AND da.courier_id = ({ACTOR}))))'
        ')'
    ),
    'delivery_assignments': (
        f'courier_id = ({ACTOR}) OR assigned_by = ({ACTOR}) '
        'OR EXISTS (SELECT 1 FROM public.orders o '
        'WHERE o.id = delivery_assignments.order_id '
        f'AND o.farmer_id = ({ACTOR}))'
    ),
    'seller_compliance': f'farmer_id = ({ACTOR})',
}


def review_select_policies():
    """Return candidate SQL for offline review only (never executes)."""
    return tuple(
        f'CREATE POLICY wp_{table}_select ON public.{table} FOR SELECT '
        f'USING ({predicate});'
        for table, predicate in SELECT_PREDICATES.items()
    )


def rollout_blockers():
    return (
        'Brak zintegrowanych transakcji uwierzytelnionych we wszystkich endpointach.',
        'Brak polityk INSERT/UPDATE/DELETE i procesu logowania przed ustawieniem kontekstu.',
        'Ryzyko rekurencji polityk orders / order_locations / delivery_assignments.',
        'Konto SQL może ustawiać dowolne custom GUC; brak izolacji od arbitralnego SQL.',
        'Brak testów integracyjnych na prawdziwym PostgreSQL i testów ról.',
        'Polityki na poziomie wiersza nie ukrywają kolumn pin_hash ani danych adresowych.',
    )
