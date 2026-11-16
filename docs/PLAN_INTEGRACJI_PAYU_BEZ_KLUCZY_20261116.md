# WiejskaPaka — przygotowanie integracji PayU (bez kluczy i bez uruchamiania płatności)
Data: 2026-11-16. Dokument roboczy na gałęzi WIEJSKAPAKA-FINAL-WYGLAD-RLS-REKLAMY-20261116.

## Zasada bezpieczeństwa
Nie zmieniać zaakceptowanego UI, istniejących zabezpieczeń RLS ani sald w trakcie przygotowania. Integrację wykonać na osobnej gałęzi od zweryfikowanej wersji demo; środowisko TEST/SANDBOX domyślne, produkcja zablokowana do odrębnego zatwierdzenia. Nie zapisywać sekretów w repozytorium ani w logach.

## Decyzje wymagające potwierdzenia przez PayU i prawnika
- Czy PayU obsłuży zamierzony model marketplace, przyjmowanie środków od klientów, przechowywanie sald, rozliczanie wielu sprzedawców oraz wypłaty na rachunki klientów i sprzedawców. Zwykła integracja płatności PayU nie jest równoznaczna z legalnym prowadzeniem portfela pieniężnego.
- Kto jest merchant of record, kto trzyma środki, kto wykonuje KYC/KYB, jakie są terminy settlement, chargebacki i opłaty.
- Jak rozliczać opłatę 5% od wypłaty sprzedawcy, brak prowizji WiejskaPaka od wypłaty klienta, opłaty operatora, zwroty i korekty.
- Czy istnieje osobny produkt/API PayU do wypłat i split settlement; nie zakładać, że standardowy endpoint płatności potrafi to zrobić.
- Weryfikacja podatkowa, regulaminu, rachunkowości i AML przed produkcją.

## Przygotowanie techniczne
1. Zrobić inwentaryzację istniejących endpointów portfela, zamówień, PIN, księgi groszowej, zwrotów i uprawnień. Nie zakładać nazw plików ani tabel bez odczytu repozytorium.
2. Zdefiniować adapter PaymentProvider z metodami: create_topup, get_payment_status, verify_notification, request_refund oraz osobny PayoutProvider, tylko jeśli PayU faktycznie obsługuje wymagane wypłaty.
3. Stan wpłaty: CREATED -> PENDING -> CONFIRMED lub FAILED/CANCELLED. Saldo zasilać tylko po zweryfikowanym po stronie serwera potwierdzeniu od operatora; przekierowanie przeglądarki nie jest dowodem zapłaty.
4. Każdy event i operacja muszą mieć unikatowy identyfikator i idempotentne księgowanie. Duplikat webhooka nie może drugi raz zasilić portfela.
5. Weryfikować autentyczność notyfikacji dokładnie zgodnie z aktualną dokumentacją PayU, w tym sprawdzenie statusu u operatora, jeśli wymagane. Nie opierać zaufania na polach dostarczonych przez przeglądarkę.
6. Pieniądze: integer grosze, brak float, jawne reguły zaokrągleń i rozdziału reszty, spójność salda z księgą. Każda operacja powinna być transakcyjna.
7. Wypłaty: stany REQUESTED/PROCESSING/PAID/FAILED/REVERSED, zabezpieczenie przed podwójną wypłatą i blokada dostępnego salda podczas realizacji. Prowizja sprzedawcy 5% ma być jawnie pokazana; wypłata klienta bez prowizji platformy.
8. Zwroty: pełny zwrot przy niedostarczeniu z winy dostawcy; rozliczenie salda, operatora, prowizji i już zrealizowanych wypłat bez tworzenia pieniędzy.
9. Sekrety wyłącznie z managera sekretów/zmiennych środowiskowych, odrębne TEST/PROD, maskowanie logów, rotacja i minimalne uprawnienia.
10. Przed aktywacją: testy integracyjne na sandbox, duplikaty i opóźnienia webhooków, równoległe żądania, przerwy sieciowe, częściowe zwroty, odmowy, chargebacki, pojednanie dzienne i kontrola RLS.

## Warunki uruchomienia produkcji
Potwierdzony model przez PayU; aktywowane konto i właściwe usługi; podpisane umowy i zgodność prawna; komplet pozytywnych testów sandbox i co najmniej kontrolowana płatność na środowisku produkcyjnym za zgodą właściciela; monitoring i procedura rozliczania rozbieżności. Dopiero potem przełączyć flagę produkcyjną.

## Status
To jest plan wdrożeniowy, nie działająca integracja. Nie utworzono kluczy PayU, nie wykonano transakcji, nie zmieniono portfela ani produkcyjnego VPS.
