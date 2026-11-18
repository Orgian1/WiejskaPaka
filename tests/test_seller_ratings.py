"""Isolated SQLite tests for seller rating authorization and aggregation."""
import sqlite3
import unittest

from fastapi import HTTPException
from backend.seller_ratings import SCHEMA_SQLITE, rate_completed_order, seller_rating_summary


class SellerRatingsTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        self.con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY)")
        self.con.executemany("INSERT INTO users(id) VALUES(?)", [(1,), (2,), (3,)])
        self.con.execute("""CREATE TABLE orders(
            id INTEGER PRIMARY KEY, buyer_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL, status TEXT NOT NULL)""")
        self.con.executemany(
            "INSERT INTO orders(id,buyer_id,farmer_id,status) VALUES(?,?,?,?)",
            [(10,1,2,"odebrane"), (11,1,2,"gotowe_do_odbioru_testowo"),
             (12,3,2,"odebrane")],
        )
        self.con.executescript(SCHEMA_SQLITE)

    def tearDown(self):
        self.con.close()

    def test_only_buyer_of_completed_order_can_rate(self):
        result = rate_completed_order(self.con, 1, 10, 5)
        self.assertEqual(result["stars"], 5)
        self.assertEqual(seller_rating_summary(self.con, 2),
                         {"seller_id": 2, "count": 1, "average": 5.0})

    def test_other_buyer_cannot_rate_order(self):
        with self.assertRaises(HTTPException) as caught:
            rate_completed_order(self.con, 3, 10, 5)
        self.assertEqual(caught.exception.status_code, 404)

    def test_pending_order_cannot_be_rated(self):
        with self.assertRaises(HTTPException) as caught:
            rate_completed_order(self.con, 1, 11, 5)
        self.assertEqual(caught.exception.status_code, 409)

    def test_duplicate_rating_rejected(self):
        rate_completed_order(self.con, 1, 10, 5)
        with self.assertRaises(HTTPException) as caught:
            rate_completed_order(self.con, 1, 10, 1)
        self.assertEqual(caught.exception.status_code, 409)

    def test_out_of_range_rating_rejected(self):
        for invalid in (0, 6, True, 2.5):
            with self.subTest(stars=invalid):
                with self.assertRaises(HTTPException) as caught:
                    rate_completed_order(self.con, 1, 10, invalid)
                self.assertEqual(caught.exception.status_code, 422)

    def test_average_across_distinct_orders(self):
        rate_completed_order(self.con, 1, 10, 5)
        rate_completed_order(self.con, 3, 12, 3)
        self.assertEqual(seller_rating_summary(self.con, 2),
                         {"seller_id": 2, "count": 2, "average": 4.0})

    def test_second_buyer_can_rate_only_their_own_order(self):
        rate_completed_order(self.con, 1, 10, 5)
        rate_completed_order(self.con, 3, 12, 1)
        self.assertEqual(seller_rating_summary(self.con, 2),
                         {"seller_id": 2, "count": 2, "average": 3.0})

    def test_database_prevents_duplicate_even_without_precheck(self):
        rate_completed_order(self.con, 1, 10, 5)
        cursor = self.con.execute(
            "INSERT INTO seller_ratings(order_id,buyer_id,seller_id,stars) "
            "VALUES(?,?,?,?) ON CONFLICT(order_id) DO NOTHING",
            (10, 1, 2, 1),
        )
        self.assertEqual(cursor.rowcount, 0)
        self.assertEqual(seller_rating_summary(self.con, 2)["average"], 5.0)

    def test_no_ratings_yet(self):
        self.assertEqual(seller_rating_summary(self.con, 2),
                         {"seller_id": 2, "count": 0, "average": None})


if __name__ == "__main__":
    unittest.main()
