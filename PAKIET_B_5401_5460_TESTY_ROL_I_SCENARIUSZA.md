# WiejskaPaka B/5401–B/5460 — kontrola ról, błędów logowania i scenariusza zakupowego

Data: 2026-10-15.

## Wyniki rzeczywiście wykonane

- `python -m scripts.check_roles_offline`: PASS — 12 kombinacji (4 role × 3 szerokości: 320, 390, 1280 px), logowanie, widoczność paneli, wylogowanie, brak poziomego przewijania. Chromium z mockiem API, nie rzeczywisty serwer.
- `python -m scripts.check_auth_failures_offline`: PASS — 3 przypadki: odrzucone logowanie, nieważny profil/sesja, błąd sieci. Chromium z mockiem API.
- `python -m scripts.check_demo_readiness`: PASS — strona i zasoby serwowane przez FastAPI TestClient; scenariusz zakupowy na jednorazowej SQLite (odbiór, dostawa, PIN jednorazowy, prywatność adresu, grosze).
- `python -m scripts.audit_mobile_markup`: PASS — 55 identyfikatorów, 6 linków, 3 zasoby.
- `python -m scripts.check_mobile_offline`: PASS — Chromium offline na 3 rozdzielczościach.

## Ograniczenia / niewykonane

- `python -m scripts.check_postgres_security`: ODMOWA WYKONANIA — wymaga jawnego opt-in `WP_READONLY_PG_PREFLIGHT=YES_I_CONFIRM`; nie ustawiano flagi, nie łączono się z Neon.
- `python -m scripts.audit_test_payments` bez argumentu: NIEURUCHOMIONY AUDYT — wymaga `--sqlite` wskazującego bazę testową; nie ma wyniku audytu płatności w tym pakiecie.
- Brak fizycznych telefonów i testu Chromium z realnym API przez localhost (blokada środowiska wykazana wcześniej).
- Nie wprowadzono zmian do kodu aplikacji, testów, konfiguracji Neon ani płatności produkcyjnych. Raport 211/211 regresji dotyczy tego samego kodu aplikacji.

## Kolejne działania

1. Audyt testowych płatności na przygotowanej izolowanej bazie SQLite.
2. Uruchomienie lokalnego PostgreSQL na odrębnej bazie testowej, jeśli środowisko będzie dostępne.
3. Test end-to-end z rzeczywistym API w przeglądarce na środowisku, które nie blokuje localhost.
4. Testy fizycznych telefonów i przegląd bezpieczeństwa przed wydaniem.
