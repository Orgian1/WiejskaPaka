"""Human-readable shipment references; internal shipment IDs remain immutable."""
import string


def point_letter(con, farmer_id, pickup_point_id):
    if pickup_point_id is None:
        return "D"  # Delivery to address has its own sequence.
    rows = con.execute(
        "SELECT id FROM pickup_points WHERE farmer_id=? ORDER BY id",
        (farmer_id,),
    ).fetchall()
    ids = [int(row["id"]) for row in rows]
    if pickup_point_id not in ids:
        raise ValueError("Punkt odbioru nie należy do sprzedawcy")
    index = ids.index(pickup_point_id)
    if index >= 26:
        raise ValueError("Format literowy obsługuje do 26 punktów odbioru")
    return string.ascii_uppercase[index]


def display_shipment_number(con, farmer_id, pickup_point_id, shipment_id, pin):
    """Compute a point-local sequential number in the checkout transaction.

    Shipment group rows are created in a serialized checkout transaction.
    A shipment with multiple products counts once. The technical ID is never
    replaced in database keys, URLs or payment/idempotency records.
    """
    if len(pin) != 6 or not pin.isascii() or not pin.isdigit():
        raise ValueError("PIN musi mieć sześć cyfr")
    letter = point_letter(con, farmer_id, pickup_point_id)
    if pickup_point_id is None:
        rows = con.execute(
            """SELECT id FROM shipment_groups
               WHERE farmer_id=? AND fulfillment='dostawa'
               ORDER BY created_at,id""",
            (farmer_id,),
        ).fetchall()
    else:
        rows = con.execute(
            """SELECT DISTINCT g.id,g.created_at
               FROM shipment_groups g
               JOIN shipment_order_links l ON l.shipment_id=g.id
               JOIN order_locations ol ON ol.order_id=l.order_id
               WHERE g.farmer_id=? AND ol.pickup_point_id=?
               ORDER BY g.created_at,g.id""",
            (farmer_id, pickup_point_id),
        ).fetchall()
    ids = [row["id"] for row in rows]
    if shipment_id not in ids:
        raise ValueError("Przesyłka nie została przypisana do punktu")
    ordinal = ids.index(shipment_id) + 1
    return f"{letter}{ordinal:03d}-{pin[:3]}"
