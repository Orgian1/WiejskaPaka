"""Live HTTP smoke check of the approved local demo, isolated from real services."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


class LiveDemoHTTPTests(unittest.TestCase):
    def test_approved_ui_assets_and_rating_endpoint_over_http(self):
        with tempfile.TemporaryDirectory(prefix="wp_http_demo_") as directory:
            root = Path(directory)
            sample = root / "sample"
            env = {k: v for k, v in os.environ.items()
                   if k not in ("DATABASE_URL", "WP_AUTO_INIT_POSTGRES")}
            env.update(WIEJSKAPAKA_ENV="development", WP_ENV="development",
                       WIEJSKAPAKA_DB=str(sample / "demo.sqlite3"),
                       WP_ENABLE_TEST_PAYMENTS="1")
            seed = subprocess.run(
                [sys.executable, "-m", "scripts.prepare_sample_demo",
                 "--full-demo", "--directory", str(sample)],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(seed.returncode, 0, seed.stderr)
            self.assertEqual(json.loads(seed.stdout)["database"], env["WIEJSKAPAKA_DB"])
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "backend.app:app",
                 "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
                cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, text=True,
            )
            try:
                base = "http://127.0.0.1:" + str(port)
                for attempt in range(100):
                    if server.poll() is not None:
                        self.fail("Demo server stopped before HTTP check: " + server.stderr.read()[-3000:])
                    try:
                        with urlopen(base + "/", timeout=1) as response:
                            html = response.read().decode("utf-8")
                            self.assertEqual(response.status, 200)
                        break
                    except (URLError, TimeoutError):
                        time.sleep(0.1)
                else:
                    self.fail("Demo did not start within 10 seconds")
                self.assertIn("/assets/app.js", html)
                self.assertIn("/assets/app-views.js", html)
                for asset, required in [
                    ("/assets/app.js", "catalogPage"),
                    ("/assets/app-views.js", "sellerRatingsByProduct"),
                    ("/assets/wallet-ads.js", "enterWalletWithAd"),
                ]:
                    with urlopen(base + asset, timeout=3) as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(required, response.read().decode("utf-8"))
                with urlopen(base + "/sellers/1/rating", timeout=3) as response:
                    rating = json.load(response)
                    self.assertEqual(response.status, 200)
                    self.assertEqual(rating["seller_id"], 1)
                    self.assertIn("count", rating)
                    self.assertIn("average", rating)
            finally:
                server.terminate()
                try:
                    server.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
