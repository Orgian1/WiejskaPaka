"""Read-only access entrypoints: actor identity comes only from a verified session.

Caller must open a database transaction on the same connection. These helpers
are not a substitute for PostgreSQL RLS or application endpoint integration.
"""
from .neon_session_bridge import verified_actor
from .neon_order_access import (
    buyer_orders, farmer_orders, courier_active_delivery_addresses,
)


def my_buyer_orders(connection, authorization, *, now=None):
    with verified_actor(connection, authorization, now=now) as actor_id:
        return buyer_orders(connection, actor_id)


def my_farmer_orders(connection, authorization, *, now=None):
    with verified_actor(connection, authorization, now=now) as actor_id:
        return farmer_orders(connection, actor_id)


def my_courier_addresses(connection, authorization, *, now=None):
    with verified_actor(connection, authorization, now=now) as actor_id:
        return courier_active_delivery_addresses(connection, actor_id)
