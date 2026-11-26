"""End-to-end smoke test for private, disposable full-demo fixture creation."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class FullDemoSeedTests(unittest.TestCase):
    def test_full_demo_has_separate_ads_and_clean_first_impression(self):
        with tempfile.TemporaryDirectory(prefix="wp_demo_test_") as root:
            destination = Path(root) / "fresh"
            result = subprocess.run(
                [sys.executable, "-m", "scripts.prepare_sample_demo",
                 "--full-demo", "--directory", str(destination)],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True, text=True, timeout=120,
                env={key: value for key, value in os.environ.items()
                     if key not in ("DATABASE_URL", "WP_AUTO_INIT_POSTGRES")},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["database"], str(destination / "demo.sqlite3"))
            self.assertEqual(payload["summary"]["orders"], 4)
            connection = sqlite3.connect(payload["database"])
            try:
                ads = connection.execute(
                    "SELECT audience, image FROM wallet_ads WHERE enabled=1 AND deleted=0"
                ).fetchall()
                self.assertEqual({audience for audience, _ in ads}, {"klient", "rolnik"})
                self.assertTrue(all(image.startswith("data:image/jpeg;base64,") for _, image in ads))
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM wallet_ad_impressions"
                ).fetchone()[0], 0)
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM wallet_ad_accounts WHERE last_shown>0"
                ).fetchone()[0], 0)
            finally:
                connection.close()


    def test_incubator_demo_seeds_only_simulated_documents(self):
        with tempfile.TemporaryDirectory(prefix="wp_incubator_demo_") as root:
            destination = Path(root) / "fresh"
            result = subprocess.run(
                [sys.executable, "-m", "scripts.prepare_sample_demo", "--full-demo",
                 "--incubator-demo", "--directory", str(destination)],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["summary"]["orders"], 4)
            connection = sqlite3.connect(payload["database"])
            try:
                entries = connection.execute("""SELECT kind, mode, amount_grosze, invoice_number
                    FROM incubator_invoice_entries ORDER BY kind""").fetchall()
                self.assertEqual(entries, [
                    ("advertising", "test", 1299, "DEMO/1"),
                    ("refund", "test", 199, None),
                    ("withdrawal_fee", "test", 201, None),
                ])
                wallet = connection.execute("""SELECT available_grosze, reserved_grosze
                    FROM wallet_preview_accounts""").fetchone()
                self.assertEqual(wallet, (5990, 0))
                self.assertEqual(connection.execute("SELECT count(*) FROM sessions").fetchone(), (0,))
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
