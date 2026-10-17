from backend.neon_rls_policy_plan import SELECT_PREDICATES, review_select_policies, rollout_blockers


def test_six_sensitive_tables_covered():
    assert set(SELECT_PREDICATES) == {'users', 'sessions', 'orders', 'order_locations', 'delivery_assignments', 'seller_compliance'}


def test_candidates_do_not_enable_rls_or_modify_data():
    sql = '\n'.join(review_select_policies())
    assert len(review_select_policies()) == 6
    assert 'ENABLE ROW LEVEL SECURITY' not in sql
    assert 'FOR SELECT' in sql
    assert 'FOR ALL' not in sql
    assert 'w_drodze_testowo' in sql
    assert 'pin_used = 0' in sql


def test_unset_actor_fails_closed_by_null_comparison():
    assert all("NULLIF(current_setting('wiejskapaka.actor_id', true), '')::bigint" in p for p in SELECT_PREDICATES.values())


def test_rollout_blockers_explicit():
    assert len(rollout_blockers()) >= 5
