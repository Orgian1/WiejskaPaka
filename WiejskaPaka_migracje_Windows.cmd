@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo [1/4] Kontrola konfiguracji i pustej bazy testowej...
python -m database.validate_migration_target
if errorlevel 1 goto :fail_preflight
echo [2/4] Weryfikacja plikow migracji...
python -m database.verify_test_migrations
if errorlevel 1 goto :fail_lock
echo [3/4] Wykonywanie 23 migracji...
echo Migracja 1/23: postgres_schema.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\postgres_schema.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 2/23: upgrade_09.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_09.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 3/23: upgrade_10.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_10.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 4/23: upgrade_11.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_11.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 5/23: upgrade_12.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_12.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 6/23: upgrade_13.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_13.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 7/23: upgrade_14.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_14.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 8/23: upgrade_16.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_16.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 9/23: upgrade_17.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_17.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 10/23: upgrade_21.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_21.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 11/23: upgrade_23.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_23.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 12/23: upgrade_25.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_25.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 13/23: upgrade_26.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_26.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 14/23: upgrade_28.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_28.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 15/23: upgrade_pack3.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_pack3.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 16/23: upgrade_b371_saved_cart.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_b371_saved_cart.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 17/23: upgrade_b561_shipments.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_b561_shipments.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 18/23: upgrade_b1681_checkout_idempotency.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_b1681_checkout_idempotency.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 19/23: upgrade_z_password_change.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_z_password_change.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 20/23: upgrade_z_checkout_pin_recovery.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_z_checkout_pin_recovery.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 21/23: upgrade_b10921_inventory_reservations.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_b10921_inventory_reservations.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 22/23: upgrade_b10921_local_marketplace.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_b10921_local_marketplace.sql"
if errorlevel 1 goto :fail_migration
echo Migracja 23/23: upgrade_b10921_purchase_records.sql
psql -X -v ON_ERROR_STOP=1 -d "%WP_TEST_DATABASE_URL%" -f "database\upgrade_b10921_purchase_records.sql"
if errorlevel 1 goto :fail_migration
echo [4/4] Weryfikacja schematu...
python -m database.verify_migrated_schema
if errorlevel 1 goto :fail_post
echo.
echo SUKCES: migracje wykonane i zweryfikowane.
exit /b 0
:fail_preflight
echo BLOKADA: baza lub konfiguracja nie przeszla kontroli. Nic nie migrowano.
exit /b 1
:fail_lock
echo BLOKADA: pliki migracji nie przeszly weryfikacji. Nic nie migrowano.
exit /b 1
:fail_migration
echo BLAD: migracja przerwana. NIE URUCHAMIAJ SKRYPTU PONOWNIE na tej bazie.
echo Testowa baza moze byc czesciowo zmieniona.
exit /b 1
:fail_post
echo BLAD: migracje wykonano, ale koncowa weryfikacja nie powiodla sie.
echo NIE URUCHAMIAJ SKRYPTU PONOWNIE na tej bazie.
exit /b 1
