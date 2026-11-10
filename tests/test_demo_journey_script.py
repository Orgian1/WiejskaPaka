"""Demo musi działać niezależnie i ignorować zewnętrzne DATABASE_URL."""
import os
import subprocess
import sys
from pathlib import Path


def test_demo_journey_isolated_from_external_database():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env['DATABASE_URL'] = 'postgresql://invalid.example/neondb'
    result = subprocess.run([sys.executable, str(root / 'scripts' / 'demo_journey.py')],
                            cwd=root, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'DEMO OK' in result.stdout
