# WiejskaPaka — publiczne demo dla reklamodawców (plan, bez wdrożenia)

## Cel i kolejność
1. Właściciel zatwierdza **właściwy wygląd** gałęzi `WIEJSKAPAKA-FINAL-WYGLAD-RLS-REKLAMY-20261116` lokalnie.
2. Dopiero potem wdrożenie demonstracyjne na własny serwer, HTTPS i domena; osobna izolowana baza demo, bez dostępu do produkcji.
3. Podłączenie skrzynki e-mail do kontaktu reklamowego. Nie publikować numerów telefonów klientów i rolników.
4. Pokaz reklamodawcom i inkubatorowi. PayU live, wypłaty, prawdziwe zamówienia i doładowania pozostają wyłączone do osobnego odbioru prawnego i płatniczego.

## Treści zastępczych reklam
- Dla klientów: **TU MOŻE BYĆ TWOJA REKLAMA!** „Dotrzyj ze swoją ofertą do klientów kupujących bezpośrednio od rolników.” „Zapytaj o reklamę na WiejskaPaka”.
- Dla rolników/sprzedawców: **TU MOŻE BYĆ TWOJA REKLAMA!** „Dotrzyj do rolników i producentów sprzedających swoje produkty.” „Zareklamuj swoją firmę na WiejskaPaka”.
- Kontakt prowadzi do formularza lub firmowej skrzynki, bez publicznych numerów użytkowników.
- Reklamy w portfelu: 5 sekund, czerwony X z odliczaniem, automatyczne zamknięcie, maksymalnie jedna emisja na konto na 30 minut.

## Ważna luka do naprawy przed publicznym demo
Obecne testy `tests/test_wallet_ads_http.py` sprawdzają, że **ta sama kampania** może trafić zarówno do klienta, jak i sprzedawcy (`claim(client,seller)` i `claim(client,other)` zwracają ten sam `aid`). Aktualny formularz administratora opisuje kampanię bez pola grupy docelowej. Nie wolno twierdzić, że osobne reklamy dla klientów i rolników są już wdrożone tylko dlatego, że testy reklam przeszły. Należy dodać wybór odbiorcy kampanii (klient / rolnik), bezpieczną migrację bazy, filtrowanie po rzeczywistej roli konta i testy separacji, a potem ponownie wykonać RLS/Chromium/HTTP. Nie zmieniać zaakceptowanego układu strony.

## Odbiór przed uruchomieniem publicznym
- Sprawdzić w przeglądarce zatwierdzony wygląd, produkty, menu i panele.
- Zweryfikować banery dla dwóch ról i brak wycieku danych między kontami.
- Wyłączyć wysyłkę produkcyjnych wiadomości, płatności i przelewy; oferty demonstracyjne oznaczyć jako przykładowe.
- Zabezpieczyć administrację, sesje, HTTPS, kopie zapasowe i konfigurację poczty.
- Po testach na serwerze właściciel zatwierdza publikację.
