"""Seller ratings: one verified 1–5-star review per completed order.

This module is intentionally isolated from the approved UI. Installation into
the application and PostgreSQL RLS migration require separate review.
"""
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS seller_ratings (
 order_id INTEGER PRIMARY KEY REFERENCES orders(id),
 buyer_id INTEGER NOT NULL REFERENCES users(id),
 seller_id INTEGER NOT NULL REFERENCES users(id),
 stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS seller_ratings_seller_idx ON seller_ratings(seller_id);
"""


class RatingInput(BaseModel):
    model_config = {"extra": "forbid"}
    order_id: int = Field(strict=True, gt=0)
    stars: int = Field(strict=True, ge=1, le=5)


def rate_completed_order(con, buyer_id: int, order_id: int, stars: int):
    """The order itself is the source of truth for review eligibility."""
    if type(stars) is not int or not 1 <= stars <= 5:
        raise HTTPException(422, "Ocena musi wynosić od 1 do 5 gwiazdek")
    order = con.execute(
        "SELECT id,buyer_id,farmer_id,status FROM orders WHERE id=?",
        (order_id,),
    ).fetchone()
    if order is None or order["buyer_id"] != buyer_id:
        raise HTTPException(404, "Nie znaleziono Twojego zamówienia")
    # Fail closed: only the final, confirmed states are eligible.
    if order["status"] not in ("odebrane",):
        raise HTTPException(409, "Możesz ocenić sprzedawcę dopiero po zakończeniu zamówienia")
    if con.execute("SELECT 1 FROM seller_ratings WHERE order_id=?", (order_id,)).fetchone():
        raise HTTPException(409, "To zamówienie zostało już ocenione")
    con.execute(
        "INSERT INTO seller_ratings(order_id,buyer_id,seller_id,stars) VALUES(?,?,?,?)",
        (order_id,buyer_id,order["farmer_id"],stars),
    )
    return {"order_id": order_id, "seller_id": order["farmer_id"], "stars": stars}


def seller_rating_summary(con, seller_id: int):
    row = con.execute(
        "SELECT COUNT(*) AS count, SUM(stars) AS total FROM seller_ratings WHERE seller_id=?",
        (seller_id,),
    ).fetchone()
    count = row["count"]
    return {"seller_id": seller_id, "count": count,
            "average": round(row["total"] / count, 2) if count else None}
