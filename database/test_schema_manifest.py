"""Offline, immutable manifest for provisioning a NEW disposable test database.

Does not connect to a database or execute SQL. SQL scripts are applied manually
by an operator after reviewing this plan and confirming an empty test database.
"""
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'postgres_schema.sql'
UPGRADES = (
    'upgrade_09.sql', 'upgrade_10.sql', 'upgrade_11.sql',
    'upgrade_12.sql', 'upgrade_13.sql', 'upgrade_14.sql',
    'upgrade_16.sql', 'upgrade_17.sql', 'upgrade_21.sql',
    'upgrade_23.sql', 'upgrade_25.sql', 'upgrade_26.sql',
    'upgrade_28.sql', 'upgrade_pack3.sql',
    'upgrade_b371_saved_cart.sql', 'upgrade_b561_shipments.sql',
    'upgrade_b1681_checkout_idempotency.sql',
    'upgrade_z_password_change.sql',
    'upgrade_z_checkout_pin_recovery.sql',
    'upgrade_b10921_inventory_reservations.sql',
    'upgrade_b10921_local_marketplace.sql',
    'upgrade_b10921_purchase_records.sql',
    'upgrade_z_password_reset_test.sql',
    'upgrade_z_support_cases_test.sql',
    'upgrade_z_reset_mail_queue.sql',
    'optional_product_sale_units.sql',
    'optional_address_delivery.sql',
    'optional_user_photos.sql',
    'optional_seller_directory.sql',
    'optional_order_mail_outbox.sql',
    'optional_email_verification.sql',
    'optional_mail_send_budget.sql',
    'optional_mail_suppression.sql',
    'optional_ses_feedback.sql',
    'optional_ses_feedback_review.sql',
)


def build_manifest(root=ROOT):
    """Fail closed if a required SQL script is missing or unexpectedly empty."""
    root = Path(root)
    result = []
    for name in (BASE, *UPGRADES):
        path = root / name
        if not path.is_file() or not path.read_bytes().strip():
            raise ValueError(f'Missing or empty SQL migration: {name}')
        content = path.read_bytes()
        result.append({'file': name, 'sha256': sha256(content).hexdigest(), 'bytes': len(content)})
    return result


def required_startup_tables_covered(root=ROOT):
    """Static guard only: CREATE TABLE declarations do not prove successful SQL execution."""
    import re
    from backend.postgres_schema_preflight import CORE_TABLES
    text = '\n'.join((Path(root) / name).read_text() for name in (BASE, *UPGRADES))
    created = set(re.findall(r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z_0-9]*)\s*\(', text, re.I))
    return sorted(set(CORE_TABLES) - created)
