"""A local test mailbox on PostgreSQL requires separate, explicit authorization."""
import os
import pytest
from backend.password_reset import postgres_demo_reset_allowed
from scripts.run_phone_demo import demo_environment
from scripts.run_tests_isolated import test_environment as isolated_environment

DSN='postgresql://a:b@127.0.0.1:5432/wp_test_reset'
ENV={'WP_ENV':'test','WP_ENABLE_PG_TEST_PASSWORD_RESET':'1'}


def test_ordinary_postgres_configuration_cannot_enable_local_mailbox():
    assert not postgres_demo_reset_allowed({'WP_ENV':'test'},DSN)


@pytest.mark.skipif(os.name!='posix',reason='Private PostgreSQL mailbox is POSIX only')
def test_explicit_local_test_configuration_is_accepted():
    assert postgres_demo_reset_allowed(ENV,DSN)


@pytest.mark.parametrize('dsn',[
    'postgresql://a:b@example.invalid/wp_test_reset',
    'postgresql://a:b@127.0.0.1/production',
    'postgresql://a:b@127.0.0.1/wp_test_reset?hostaddr=198.51.100.1',
    'postgresql://a:b@127.0.0.1/wp_test_reset?service=other',
    'dbname=wp_test_reset',
])
def test_reject_unsafe_targets_without_exposing_dsn(dsn):
    with pytest.raises(ValueError) as error:postgres_demo_reset_allowed(ENV,dsn)
    assert str(error.value)=='Nieprawidlowa konfiguracja testowego resetu PostgreSQL'
    assert dsn not in str(error.value)


@pytest.mark.parametrize('extra',[{'WP_ENV':'production'},{'PGHOSTADDR':'198.51.100.1'},
    {'PGSERVICE':'private'},{'PGSERVICEFILE':'private'}])
def test_refuse_production_mode_and_inherited_routing(extra):
    with pytest.raises(ValueError):postgres_demo_reset_allowed({**ENV,**extra},DSN)


@pytest.mark.parametrize('builder',[demo_environment,isolated_environment])
def test_demo_and_test_children_strip_inherited_postgres_reset_flag(builder,tmp_path):
    env=builder({'WP_ENABLE_PG_TEST_PASSWORD_RESET':'1','WP_ENABLE_TEST_PASSWORD_RESET':'1',
                 'WP_TEST_RESET_OUTBOX':'private'},tmp_path/'db')
    assert not {'WP_ENABLE_PG_TEST_PASSWORD_RESET','WP_ENABLE_TEST_PASSWORD_RESET','WP_TEST_RESET_OUTBOX'} & env.keys()
