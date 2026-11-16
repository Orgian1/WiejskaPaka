# WiejskaPaka — kandydat demo 2026-11-16

Gałąź: integration/demo-final-candidate-20261116
Baza: codex/seller-ratings-20261116 (PR #64), zawiera PR #63 (reklamy portfela) i #62 (RLS API).

## Zweryfikowane przez przegląd GitHub
- Porównanie gałęzi #62 -> #64: HEAD ahead 10, behind 0.
- Porównanie #63 -> #64: HEAD ahead 4, behind 0.
- Istnieją pliki migracji: database/security_rls/001_gateway.up.sql, 002_wallet_ads.up.sql, 003_seller_ratings.up.sql.
- Raporty Codex: 5078 PASS, 0 FAIL, 2 SKIP (pełna regresja po uzupełnieniu); PostgreSQL FORCE RLS 168 PASS; 149/149 tras API 2xx.
- Powyższe wyniki pochodzą z raportów Codex; nie zostały niezależnie odtworzone w tej kontroli.

## Bramy przed uruchomieniem demo na VPS
1. Nie zmieniać działającej wersji, głównej bazy ani PayU. Ustalić aktualny commit, konfigurację, role DB i usługi.
2. Zabezpieczyć backup oraz wykonać test odtworzenia na izolowanej kopii; sprawdzić role, ACL, własność tabel, brak BYPASSRLS/SUPERUSER i zarządzanie kluczem gateway.
3. Na nowej jednorazowej bazie PostgreSQL uruchomić bramkę: python -m scripts.run_rls_api_gate. Nie stosować historycznego database/security_review/002_rls.up.sql.
4. Sprawdzić w izolacji migracje security_rls 001, 002, 003 i bezpieczny rollback; nie ustawiać api_compatibility_verified=yes bez realnej weryfikacji.
5. Uruchomić osobne demo z osobną bazą i portem. Zweryfikować logowanie, zakup, odbiór PIN, dostawę, saldo i wypłaty testowe, reklamy 5 sekund i 30 minut oraz oceny po odbiorze.
6. Sprawdzić widoki 320/1280 px, odświeżenie, zmianę konta, brak kampanii i awarię reklam, uprawnienia administratora.
7. Dopiero po udanym odbiorze i planie wycofania rozważyć zmianę podglądu; produkcja i rzeczywiste płatności pozostają osobnym etapem.

## Status
Kod skonsolidowany w kandydacie; testy i migracje na docelowym środowisku: NIE WYKONANE. Bez zmian na VPS.

## Dodatkowe testy integracyjne na kandydacie
- Granica limitu reklam: tests/test_wallet_ads_http.py::test_wallet_ad_exact_30_minute_boundary
- Pełna ścieżka zakupu/odbioru/oceny/portfela: tests/test_demo_purchase_pin_rating_wallet_ads.py
- Uruchomienie lokalne na jednorazowej bazie: python -m pytest -q tests/test_wallet_ads_http.py tests/test_demo_purchase_pin_rating_wallet_ads.py tests/test_seller_ratings_http.py
- Status: testy dodane do repozytorium, jeszcze NIE uruchomione w tej kontroli. Nie traktować ich jako PASS bez logów.
