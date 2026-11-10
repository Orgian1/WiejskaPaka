"""Read-only check for the core PostgreSQL schema needed by API flows.

Not a replacement for migrations, RLS verification or integration tests.
"""

CORE_TABLES = (
    'users', 'sessions', 'login_attempts', 'products', 'farmer_profiles',
    'pickup_points', 'orders', 'order_locations', 'delivery_assignments',
    'order_events', 'notifications',
    'inventory_reservations', 'order_purchase_records', 'pickup_point_coordinates',
)


def check_core_schema(connection):
    """Check public schema in a single parameterized, read-only query."""
    rows = connection.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s AND table_type = %s AND table_name = ANY(%s)",
        ('public', 'BASE TABLE', list(CORE_TABLES)),
    ).fetchall()
    found = {row['table_name'] if isinstance(row, dict) else row[0] for row in rows}
    missing = sorted(set(CORE_TABLES) - found)
    return {'checked': len(CORE_TABLES), 'found': len(found), 'missing': missing,
            'core_schema_complete': not missing, 'ready_for_public_launch': False}
