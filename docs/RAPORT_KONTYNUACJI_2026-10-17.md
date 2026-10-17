# WiejskaPaka — kontynuacja stabilizacji, 17.10.2026

Punkt wyjścia: lokalny commit `bc4f8d45ce26e2c2fd765cc4fc18e53b30e05394` na
`wiejskapaka-import`. Poprzednie wyniki zachowano w
`RAPORT_NAPRAW_2026-10-17.md`; nie stanowią dowodu bieżącej wersji.

## Naprawione problemy

1. **Dodatkowe runnery dziedziczyły konfigurację zewnętrzną.**
   `run_isolated_pytest.py` i `run_http_acceptance_suite.py` uruchamiały dzieci
   bez sanitacji konfiguracji. `run_security_focus_isolated.py` usuwał część
   ustawień PostgreSQL, ale pozostawiał `WP_CHECKOUT_KEY_FILE`. Wszystkie trzy
   używają teraz wspólnej funkcji izolacji, osobnej tymczasowej SQLite dla
   każdego zadania/modułu oraz UTF-8. Funkcja usuwa także standardowe parametry
   libpq (`PGPASSWORD`, `PGSERVICE`, `PGHOST` itd.) i opcję auto-inicjalizacji.
   Nowe próby z syntetyczną konfiguracją rodzica i prawdziwymi procesami Python
   odtworzyły **3 błędne przypadki przed poprawką** i przechodzą po zmianie.
   Nie otwierano żadnej zewnętrznej bazy ani istniejącego klucza.
2. **Raport nie może oznaczać sukcesu po zmianie źródeł.** Dodano zapisy
   atomowe i niekompletne checkpointy w czasie pracy. Pusta lista akceptacji
   nie daje PASS. Diagnostyka ma limit czasu; timeout i błąd uruchomienia
   oznaczają niepowodzenie. Zmiana testu lub kodu w trakcie pracy unieważnia
   wynik. Runner bezpieczeństwa nie ponawia starego PASS po zmianie JS,
   SQL, narzędzi, zależności lub dodaniu nowego pliku kodu.
3. **Brama natywnego PostgreSQL używała `sorted(glob(...))` zamiast manifestu.**
   Odczytuje teraz SQL w zatwierdzonej kolejności i sprawdza lock oraz sumy
   kontrolne jeszcze przed nawiązaniem połączenia i utworzeniem losowej bazy.
   Zapisuje treść SQL w pamięci i ponownie sprawdza hash po odczycie, aby zmiana
   pliku między weryfikacją i użyciem powodowała bezpieczną odmowę.
   Odczyt SQL jest jawnie w UTF-8. Testy tych odmów są offline, z kontrolowaną
   makietą połączenia, i **nie oznaczają zaliczenia natywnej integracji**.
4. **Nieaktualna kontrola nawigacji mobilnej.** Skrypt nadal oczekiwał pięciu
   linków i klikał drugi link jako katalog; interfejs ma sześć linków po dodaniu
   wyszukiwania w okolicy. Teraz sprawdza pełną listę celów i wybiera katalog
   po jego identyfikatorze. Test porównuje ten kontrakt z aktualnym HTML.
   Nie zmieniano interfejsu użytkownika ani nie deklarowano renderingu Chromium.

## Wykonana weryfikacja

- Paczka po końcowych poprawkach: **19 PASS, 0 FAIL, 0 SKIP**, cztery moduły.
- Rzeczywista akceptacja loopback HTTP: **4/4 zadania PASS**,
  `complete: true`, `passed: true`, `sources_unchanged: true`.
  Obejmuje lokalny serwer, zakup, dostawę, pełny zwrot, koszyk wielu rolników
  oraz testy prywatności i pojedynczej opłaty za dostawę.
- Próby timeoutu, pustego zestawu, zmiany źródła i nieaktualnego checkpointu
  potwierdzają odmowę sukcesu, a nie rzeczywiste awarie produkcyjne.
- Rzeczywiste uruchomienie diagnostyki `--limit 3`: **3/3 moduły PASS**,
  osobne procesy i SQLite, raport kompletny i bez zmian źródeł.
- `git diff --check`: PASS.

Runnery dodatkowe i główna regresja używają istniejących, różnych funkcji
fingerprintu (główna uwzględnia też pliki zależności). Ich skróty nie muszą
być równe; nie łączymy ich jako jednego identyfikatora dowodu.

## Pełna regresja końcowa

**3424 PASS, 0 FAIL, 17 SKIP — 3441 przypadków,
276/276 modułów.** `complete: true`, `success: true`, `sources_unchanged: true`.
Odcisk głównej regresji: `301f7931d41d6ca3146b48f0d311093646d73b3bee4ae62e87039143e261f524`.
Pełną regresję uruchomiono po ostatniej zmianie kodu; nie sumujemy z nią powtórek
ani dodatkowych zadań HTTP. Zestawienie bez logów i lokalnych ścieżek:
[`audits/regression_2026-10-17_v2_summary.json`](audits/regression_2026-10-17_v2_summary.json).

Pominięcia (nie są wynikami PASS):

- `test_mobile_offline.py`: 1 SKIP.
- `test_postgres_environment.py`: 2 SKIP.
- `test_postgres_full_api_optin.py`: 11 SKIP.
- `test_postgres_transaction_integration_optional.py`: 2 SKIP.
- `test_roles_offline.py`: 1 SKIP.

## Niewykonane bramy i gotowość

- Chromium nie jest dostępne. Próba standardowej instalacji Playwright
  zakończyła się błędem uszkodzonego/niepełnego archiwum. Nie zaliczono
  renderingu ani realnego przepływu przeglądarkowego.
- Natywny PostgreSQL pozostaje nieuruchomiony: brak serwera/Dockera,
  mapowanie UID obejmuje wyłącznie UID 0, a PostgreSQL nie obsługuje startu
  jako root. Nie obchodzono tego ograniczenia i nie użyto Neon.
- Potrzebna powtórka na Windows, 19 historycznych modułów lokalnych
  wykluczonych z repo, rzeczywiste urządzenia/przeglądarki, przegląd RLS,
  bezpieczeństwa, praw konsumenta i procedur operacyjnych.
- Wersja nadal demonstracyjna; brak gotowości produkcyjnej. Domena, hosting,
  płatności i `main` nie zostały zmienione. Nie naruszono baz, zakupów i kluczy.
  Reguły kwot całkowitych, opłaty raz na przesyłkę, PIN-u, zwrotów i prywatności
  pozostają bez zmian.
- Poprzednia próba zapisu GitHub została odrzucona błędem 403. Nie ma nowego
  potwierdzenia praw zapisu; zmiany są zachowywane lokalnie na gałęzi roboczej
  i przekazywane w paczce aktualizacji.
