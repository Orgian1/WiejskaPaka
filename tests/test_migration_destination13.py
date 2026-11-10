"""Guard against overlooked records in PostgreSQL-only tables."""
from database.migrate_all_tables import destination_tables_to_check


def test_checks_destination_only_tables():
    assert destination_tables_to_check({'users': {'id'}, 'payouts': {'id'}}, ['users']) == ['payouts', 'users']


def test_checks_source_tables_as_well():
    assert destination_tables_to_check({'users': {'id'}}, ['users', 'orders']) == ['orders', 'users']


def test_deduplicates_names():
    assert destination_tables_to_check({'users': {'id'}}, ['users', 'users']) == ['users']
