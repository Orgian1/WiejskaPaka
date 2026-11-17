# WiejskaPaka — publiczne demo dla reklamodawców (plan, bez wdrożenia)

## Cel i kolejność
1. Właściciel zatwierdza **właściwy wygląd** gałęzi `WIEJSKAPAKA-FINAL-WYGLAD-RLS-REKLAMY-20261116` lokalnie.
2. Dopiero potem wdrożenie demonstracyjne na własny serwer, HTTPS i domena; osobna izolowana baza demo, bez dostępu do produkcji.
3. Podłączenie skrzynki e-mail do kontaktu reklamowego. Nie publikować numerów telefonów klientów i rolników.
4. Pokaz reklamodawcom i inkubatorowi. PayU live, wypłaty, prawdziwe zamówienia i doładowania pozostają wyłączone do osobnego odbioru prawnego i płatniczego.

## Treści zastępczych reklam
- Dla klientów: **TUTAJ JEST MIEJSCE NA TWOJĄ REKLAMĘ — DOTRZYJ DO KLIENTÓW!**
- Dla rolników/sprzedawców: **TUTAJ JEST MIEJSCE NA TWOJĄ REKLAMĘ — DOTRZYJ DO ROLNIKÓW I SPRZEDAWCÓW!**
- Kontakt prowadzi do formularza lub firmowej skrzynki, bez publicznych numerów użytkowników.
- Reklamy w portfelu: 5 sekund, czerwony X z odliczaniem, automatyczne zamknięcie, maksymalnie jedna emisja na konto na 30 minut.

## Potwierdzony mechanizm kierowania reklam

W aktualnym kodzie `backend/wallet_ads.py` istnieje pole `audience` o wartościach `klient`, `rolnik`, `both`, a serwer wybiera kampanie według rzeczywistej roli zalogowanego konta. Panel `web/wallet-ads.js` ma wybór odbiorców. Test `test_wallet_ads_target_client_and_seller_without_cross_display` weryfikuje osobne kampanie klienta i sprzedawcy; osobny test sprawdza migrację starej bazy SQLite. Poprzednia wersja tego dokumentu błędnie opisała tę funkcję jako brakującą, opierając się na scenariuszu starszych kampanii `both`.

**Do potwierdzenia przed publicznym demo:** istniejące kampanie oznaczone `both` są celowo widoczne obu grupom; należy wybrać `klient` lub `rolnik` dla nowych dwóch własnych banerów. Na docelowej bazie PostgreSQL sprawdzić migrację i aktywne wartości pola `audience`, zanim reklamy zostaną opublikowane.

## Odbiór przed uruchomieniem publicznym
- Sprawdzić w przeglądarce zatwierdzony wygląd, produkty, menu i panele.
- Zweryfikować banery dla dwóch ról i brak wycieku danych między kontami.
- Wyłączyć wysyłkę produkcyjnych wiadomości, płatności i przelewy; oferty demonstracyjne oznaczyć jako przykładowe.
- Zabezpieczyć administrację, sesje, HTTPS, kopie zapasowe i konfigurację poczty.
- Po testach na serwerze właściciel zatwierdza publikację.
