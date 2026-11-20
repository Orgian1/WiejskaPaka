"""Explicit entitlement for a pickup point used in a test checkout."""
from datetime import timedelta
from uuid import uuid4

from backend.pickup_point_periods import now_warsaw, period_end


def grant_test_period(connection, point_id):
    start = now_warsaw() - timedelta(minutes=1)
    connection.execute(
        """INSERT INTO pickup_point_periods
           (id, point_id, farmer_id, starts_at, ends_at, price_grosze, kind)
           SELECT ?, id, farmer_id, ?, ?, 0, 'promotion' FROM pickup_points WHERE id=?""",
        (uuid4().hex, start.isoformat(), period_end(start).isoformat(), point_id),
    )
