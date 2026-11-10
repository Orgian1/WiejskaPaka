"""Fail-closed, parameterized PostgreSQL read operations for authenticated actors.

These helpers do not replace RLS. Use a verified session, never client-supplied IDs.
No phone numbers are selected. Delivery address is available only to a currently
assigned courier while an order is in an explicitly allowed delivery state.
"""
from .neon_identity import validate_actor_id

# The application must explicitly set this list to the actual delivery workflow
# status names after verifying the status transitions in backend/app.py.
ACTIVE_DELIVERY_STATUSES = frozenset({'w_drodze_testowo'})


def buyer_orders(connection, actor_id):
    actor_id = validate_actor_id(actor_id)
    return connection.execute(
        "SELECT id, pickup_code, product_id, quantity, total_grosze, fulfillment, status, created_at, "
        "(SELECT expires_at FROM inventory_reservations WHERE order_id=orders.id) AS reservation_expires_at "
        "FROM orders WHERE buyer_id = %s ORDER BY id DESC", (actor_id,)
    ).fetchall()


def farmer_orders(connection, actor_id):
    actor_id = validate_actor_id(actor_id)
    return connection.execute(
        "SELECT id, pickup_code, product_id, quantity, total_grosze, fulfillment, status, created_at, "
        "(SELECT expires_at FROM inventory_reservations WHERE order_id=orders.id) AS reservation_expires_at "
        "FROM orders WHERE farmer_id = %s ORDER BY id DESC", (actor_id,)
    ).fetchall()


def courier_active_delivery_addresses(connection, actor_id):
    actor_id = validate_actor_id(actor_id)
    # No address after completion, and no pickup-point orders.
    return connection.execute(
        "SELECT o.id, loc.delivery_city, loc.delivery_street, loc.delivery_postal_code "
        "FROM orders AS o "
        "JOIN delivery_assignments AS a ON a.order_id = o.id "
        "JOIN order_locations AS loc ON loc.order_id = o.id "
        "WHERE a.courier_id = %s AND o.fulfillment = 'dostawa' "
        "AND o.status = %s AND o.pin_used = 0 AND o.confirmed_at IS NULL "
        "ORDER BY o.id", (actor_id, 'w_drodze_testowo')
    ).fetchall()
