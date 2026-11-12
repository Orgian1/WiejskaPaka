# WiejskaPaka — ostatnie poprawki użytkownika (Work i rozmowy, 10–12.11.2026)

Baza: gałąź preview/footer-contact-form-20261110; nowa gałąź codex/demo-finalization-20261112. Nie zmieniaj main ani VPS. Zachowaj formularz Kontakt / Zgłoś problem w stopce (wysyłka wyłączona do czasu konfiguracji poczty).

## Priorytetowe wymagania
1. Odbiór osobisty: jeśli magazyn i ilość się zgadzają, nie wymagaj ręcznego zatwierdzenia zamówienia przez sprzedawcę; zapewnij atomową rezerwację i poprawny status po płatności testowej. Dostawa na adres wymaga akceptacji sprzedawcy albo propozycji nowego terminu z przedziałem godzin i decyzji klienta.
2. Przy odbiorze klient sprawdza produkt i podaje PIN; usuń dodatkowe potwierdzanie „klient sprawdził towar”. PIN jest jednorazowy.
3. Lokalizacja sprzedawcy: wyszukiwanie po adresie/miejscowości i wybór na mapie zamiast konieczności ręcznego podawania współrzędnych.
4. „Blisko mnie”: oferty w pobliżu wcześniej zapamiętanej lokalizacji zalogowanego użytkownika albo GPS za zgodą; obsłuż odmowę dostępu i zmianę lokalizacji.
5. Obok „Blisko mnie” zakładka „Ulubione”; serce pod ofertą, trwałe ulubione per konto.
6. Kod promocyjny na trzy darmowe punkty odbioru do wybranej daty (przykład 31.12.2026), konfigurowalny przez administratora; limit wykorzystania i zabezpieczenie przed podwójnym użyciem.
7. Dostawa liczona raz za przesyłkę, nie za produkt. Gdy dostawca nie przyjedzie z własnej winy, zwrot klientowi 100%.
8. Jeden portfel na konto; wypłata sprzedawcy z prowizją 5%, klienta bez prowizji WiejskaPaka. Kwoty w groszach, bez float, poprawne zaokrąglanie i idempotencja.
9. Bez ujawniania numerów telefonów klientów i sprzedawców. Zachowaj ustawowe prawa konsumentów i obowiązki sprzedawcy.
10. Sprawdź migracje PostgreSQL i brakujące tabele wallet_preview_terms, wallet_preview_resolutions, wallet_preview_operation_fences zgłoszone podczas kontroli VPS. Napraw i przetestuj lokalnie; NIE migruj VPS.
11. Zachowaj działające jednostki produktów, zdjęcia, raporty, e-mail w trybie testowym i pełną responsywność desktop/mobile. Nie podłączaj prawdziwego PayU.
12. Sprawdź ostatnie logi z VPS: pojedyncze 404 GET /user-photos/product/1; nie zakładaj, że nadal występuje. Portfel testowy miał poprawne 201 dla topup/withdrawal, strona i health 200. Ostatni raport lokalny: 23 PASS w scenariuszach SQLite checkout/email/restart i 130 PASS łącznie — to wyniki historyczne, nie nowe testy.

## Proces
Najpierw audyt istniejącego kodu i testów: nie implementuj ponownie funkcji już obecnych. Zabezpiecz lokalne zmiany. Pracuj w dużych paczkach, commituj na osobnej gałęzi, uruchamiaj testy jednostkowe, integracyjne, PostgreSQL i przeglądarkowe. Nie nadpisuj main, nie wdrażaj VPS, nie zmieniaj produkcyjnych danych i sekretów. Na końcu sporządź raport z dokładnymi wynikami PASS/FAIL/SKIP, commitami, otwartymi problemami i instrukcją odbioru demo.

## Dokumenty projektu
docs/ODBIOR_KONCOWY_DEMO_2026-11-10.md
docs/INTEGRACJA_CZAT_WORK_2026-11-10.md
docs/KONTAKT_I_ZGLOS_PROBLEM.md
docs/ODZYSKIWANIE_OPERACJI_PORTFELA_2026-11-10.md

## Uzupełnienie z ostatniego Work — interfejs i obsługa sprzedawcy (12.11)
13. Katalog: produkty w poziomych rzędach, kolejne rzędy pod spodem. Kliknięcie np. pomidorów rozwija szczegóły bezpośrednio pod wybranym produktem/rzędem, bez przejścia na inną stronę; zadbaj o mobile i dostępność.
14. Każde zdjęcie produktu: przycisk ulubionych w prawym dolnym rogu zdjęcia. Stan nieaktywny: puste serce z czerwoną obwódką; aktywny: pełne czerwone serce. Działanie klikalne, zsynchronizowane z zakładką Ulubione i zapisane per konto.
15. Panel sprzedawcy → Zamówienia: podsumowanie według punktów odbioru („Punkt A — 4 zamówienia”, „Punkt B — 7 zamówień”); kliknięcie punktu rozwija listę zamówień z numerami, produktami i ilościami. Nie pokazuj cudzych danych ani numerów telefonów.
16. Górny pasek sprzedawcy: „Dodaj punkt”; po najechaniu/kliknięciu menu punktów oraz „Przejdź do nawigacji”. Nawigacja powinna prowadzić przez punkty w kolejności ustawionej przez sprzedawcę, z obsługą urządzeń dotykowych. Nie wymyślaj tras ani ETA; korzystaj z obsługiwanego zewnętrznego mechanizmu nawigacji.
17. Panele sprzedawcy domyślnie zwinięte z wyjątkiem „Aktualne zamówienia” oraz „Uzupełnij towar”, które mają być rozwinięte. Stan zwijania ma być przewidywalny po przeładowaniu.
18. Zadbaj o regresję ostatnich poprawek i testy interakcji w przeglądarce dla desktopu i telefonu. Zachowaj inne funkcje projektu.

## Krytyczna instrukcja dla Codex — wybór gałęzi
Repozytorium `Orgian1/WiejskaPaka` ma domyślną gałąź `main`, na której może być tylko README. To NIE jest źródło aktualnej aplikacji. Przełącz workspace Codex na `codex/demo-finalization-20261112`, a jeżeli interfejs nie pozwala, sklonuj/fetch tę gałąź bez usuwania lokalnych zmian. Potwierdź obecność katalogów `web/`, `docs/`, `scripts/` i pliku `requirements-lock.txt`. Nie publikuj samego README, nie kopiuj `main` na gałąź roboczą i nie uruchamiaj `git reset --hard`.
