# Prywatny VPS i uwagi z ręcznych prób — 2026-10-20

## Stan potwierdzony przez operatora i zrzuty ekranu

- VPS netcup 62.83.21.165, Debian 13, Python 3.13.5, PostgreSQL 17.
- SSH działa po prywatnej zmianie hasła root. Hasła nie są zapisane w repo.
- Checkout `/opt/wiejskapaka/app`: commit
  `c1b783183d8842d3dbe75465e178367ec8637229`, tree
  `8e05d58d8757983a4d061a90dd0add6848be92af`.
- Venv `/opt/wiejskapaka/venv`; instalacja z requirements.txt (nie lock).
  `pip check` przeszedł. Wersje różnią się od historycznego CI, m.in.
  FastAPI 0.153.0, Uvicorn 0.54.0. To nie jest dowód pełnej zgodności.
- Nowa baza `wp_test_preview`, ograniczona rola `wp_preview_app`.
  Operator wykonał new-test-database.psql.example. PostgreSQL listen_addresses
  to localhost. Nie zmieniano publicznego dostępu do bazy.
- Konto systemowe wiejskapaka: uid 102, gid 105. Prywatny katalog stanu 0700.
- Klucz `/var/lib/wiejskapaka/preview.checkout-key`, utworzony skryptem jako
  użytkownik aplikacji. UWAGA: template env wskazuje checkout-key.json, ale
  checkout_keys.py wymaga końcówki .checkout-key; faktyczny env poprawiono.
- `/etc/wiejskapaka/preview.env` root 0600, katalog 0700; hasło wprowadzono
  niewidocznie przez getpass, zakodowano jako część URL. Nie wyświetlać pliku.
- Read-only check_postgres_preview.py wykonany przez systemd-run jako konto
  aplikacji: success=true. backup_restore_verified=false.
- Usługa wiejskapaka-preview active(running), loopback 127.0.0.1:8000.
  Zainstalowana i uruchomiona, ale **nie włączono startu przy bootowaniu**.
- Operator otworzył tunel SSH z Windows i załadował stronę lokalnie.
  Agent nie ma uwierzytelnionego dostępu do VPS ani przeglądarki operatora.

## Ręczne próby na VPS

- Rejestracja i logowanie klient1@example.com: potwierdzone ekranem.
- Lista sesji: ekran pokazuje 2 aktywne, 1 pozostałą.
- Wylogowanie pozostałych: operator potwierdził jedną bieżącą.
- Wylogowanie wszystkich i ponowne zalogowanie: operator potwierdził.
- Rolnik: operator utworzył `rolnik1@example.co` (bez końcowego m).
  Logowanie i panel gospodarstwa z zerową liczbą produktów/zamówień widoczne.
- Nie potwierdzono dodania produktu, zamówienia ani płatności.
- Obecne web/app.js trzyma bearer wyłącznie w pamięci: odświeżenie strony
  usuwa lokalne zalogowanie, ale nie unieważnia sesji po stronie serwera.

## Uzgodnione poprawki — nie wdrożone na VPS

1. Jednostki sprzedaży: szt., kg, g, l, ml, opak., pęczek, słoik, butelka,
   worek, skrzynka, tacka. Opakowania mają deklarowaną zawartość.
   Kg/l z ilościami ułamkowymi. W bazie ilości jako całkowite jednostki bazowe,
   pieniądze w groszach. Cena pozycji zaokrąglana half-up raz po mnożeniu.
   Opłata za dostawę nadal raz za przesyłkę.
2. Wyszukiwanie Blisko mnie: adres zamiast dwóch pól współrzędnych.
   Miejscowość, ulica/numer (bez ulicy na wsi), kod pocztowy, wybór właściwego
   miejsca przy wielu wynikach, opcja lokalizacji urządzenia. Zmiana adresu
   musi unieważnić wcześniejszy wybór i współrzędne. Nie wybierać po cichu
   pierwszego wyniku ani nie udawać dokładności punktu na podstawie miasta.
3. Utrzymanie sesji po odświeżeniu wymaga świadomego modelu cookie HttpOnly
   i CSRF; nie zapisywać bearer w localStorage jako szybkiego obejścia.

## Nowa praca w kodzie

Stan odzyskany 2026-10-21: zachowały się niezacommitowane pliki integracji
12 jednostek z API, katalogiem, koszykiem, panelem gospodarstwa i rekordami zakupu.
Flaga WP_ENABLE_PRODUCT_UNITS domyślnie wyłączona. Na tym etapie obsługiwane są
wyłącznie całkowite ilości jednostek sprzedaży (np. 2 kg); ilości ułamkowe nadal
wymagają integracji magazynu i zamówień. Nie reinterpretować starych stock/quantity
jako gramów. Stare produkty bez metadanych pozostają sztukami.

Dodano osobne, niezmienne metadane produktów i zamówień oraz migrację
optional_product_sale_units.sql. Po zapisaniu produktów innych niż sztuki
aplikacja odmawia startu z wyłączoną flagą, aby nie zmienić znaczenia cen.
Migracja PostgreSQL nie została wykonana ani przetestowana na VPS.

Poprzednia pełna regresja miała jeden błąd audytu pomijającego optional_*.sql.
Poprawiono audyt; ponowny pełny przebieg uruchomiono, ale raporty /tmp nie
przetrwały niedostępności środowiska. Nie uznawać go za zaliczony.
Odzyskane źródła wymagają ponownej regresji. VPS pozostaje na c1b7831.

Przy geokodowaniu potrzebny jest rzeczywisty dostawca/dane; publiczny Nominatim
nie dopuszcza autocomplete i ogranicza ruch całej aplikacji do 1 zapytania/s.
Nie wdrażać fikcyjnych podpowiedzi ani losowych kodów pocztowych.

Źródła do dalszego przygotowania geokodera:
- https://nominatim.org/release-docs/latest/api/Search/
- https://operations.osmfoundation.org/policies/nominatim/

## Pozostaje

Integracja obu poprawek, testy HTTP i przeglądarki, kompatybilność nowego runtime,
próba backup/restore, SSH na klucze i przegląd zabezpieczeń VPS, poczta SES,
rzeczywiste płatności i pozostałe bramki publikacji. Prywatny podgląd nie oznacza
gotowości produkcyjnej. Nie zmieniać domeny ani nie zdejmować deployment_guard.

## Potwierdzona regresja po odzyskaniu — 2026-10-21

Commit dd26b62: 330/330 modułów, 4142 passed, 0 failed, 68 skipped.
Wszystkie cztery części mają ten sam fingerprint źródeł i sources_unchanged=true.
Dowody: docs/audits/product_units_2026-10-21/. Runtime Python 3.12.14;
wersje pakietów zapisane w requirements-resolved.txt. To testy lokalne,
nie wykonanie migracji na PostgreSQL 17 ani wdrożenie na VPS.

Dodatkowa walidacja HTTP: każda z 12 jednostek przeszła zakup trzech jednostek,
sprawdzenie ceny i jednej opłaty dostawy, zachowanie pierwotnych danych po
edycji oferty oraz jednokrotne przywrócenie magazynu po anulowaniu.
Rozszerzony moduł HTTP: 18 passed, 0 failed. Źródła aplikacji bez zmian
od pełnej regresji; zmieniono wyłącznie testy i dokumentację.
