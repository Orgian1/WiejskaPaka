"""Regression checks for the five test-only payout mutations."""
import ast
import inspect
import pytest
from backend import app as module

WRITE_ROUTES = (
    'create_payout_plan_test',
    'reserve_payout_plan_test',
    'cancel_reservation_test',
    'reconcile_all_payout_reservations_test',
    'run_payout_schedule_test',
)

@pytest.mark.parametrize('name', WRITE_ROUTES)
def test_payout_mutation_reauthenticates_in_same_db_transaction(name):
    fn = getattr(module, name)
    assert 'authorization' in inspect.signature(fn).parameters
    tree = ast.parse(inspect.getsource(fn))
    with_calls = [node for node in ast.walk(tree) if isinstance(node, ast.With)]
    assert any(
        isinstance(item.context_expr, ast.Call)
        and isinstance(item.context_expr.func, ast.Name)
        and item.context_expr.func.id == 'order_write_db'
        for node in with_calls for item in node.items
    ), name


def test_payout_mutations_remain_test_only():
    for name in WRITE_ROUTES:
        src = inspect.getsource(getattr(module, name))
        assert "WP_ENABLE_TEST_PAYMENTS" in src
        assert 'require(user,' in src
