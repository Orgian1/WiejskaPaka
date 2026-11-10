"""Central policy for courier access to delivery addresses.

The caller must verify the courier identity from a server-side session and
verify assignment to the specific order. No telephone numbers are exposed.
"""

ACTIVE_DELIVERY_STATUSES = frozenset({'w_drodze_testowo'})


def courier_may_see_address(*, actor_id, courier_id, fulfillment, status,
                            pin_used, confirmed_at):
    """Fail closed until dispatched; revoke immediately after PIN confirmation."""
    return (
        type(actor_id) is int and actor_id > 0
        and type(courier_id) is int and courier_id == actor_id
        and fulfillment == 'dostawa'
        and status in ACTIVE_DELIVERY_STATUSES
        and pin_used == 0
        and confirmed_at is None
    )
