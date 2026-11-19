# WiejskaPaka — status rozliczeń miesięcznych (19.11.2026)

## Potwierdzone w testach automatycznych
- Odczyt zakończonych wypłat **testowych** sprzedawców z wybranego miesiąca UTC.
- Wyliczenie prowizji 5% na podstawie zamrożonych danych testowej wypłaty, w całkowitych groszach.
- Pomijanie wypłat klienta z prowizją 0 zł i anulowanych wypłat testowych.
- Wykrywanie nieprawidłowych identyfikatorów, brakujących źródeł, podwójnych zapisów, błędnych kwot i dat.
- Raporty kontrolne i sumy według sprzedawcy, rodzaju opłaty oraz waluty; powtarzanie raportu nie zmienia danych.
- Blokada eksportu raportu testowego jako faktury. Brak aktywnego wystawiania faktur.
- Ochrona zatwierdzonego interfejsu w osobnym workflow CI.

## Granice rozwiązania
- Dane pochodzą z tabel **wallet_preview_***; to symulacja, nie dowód rzeczywistego przelewu ani pobrania opłaty.
- Raporty obejmują wyłącznie symulowane prowizje od wypłat; brak podłączenia wiarygodnego rejestru rzeczywiście opłaconych punktów odbioru i reklam.
- Obecny raport nie ustala momentu powstania obowiązku podatkowego, stawki VAT, nabywcy ani numeracji faktur.
- Brak potwierdzonej integracji PayU, księgowości, KSeF i produkcyjnego mechanizmu uzgodnień.
- Nie należy wystawiać faktur ani deklarować przychodów na podstawie danych symulacyjnych.

## Następne zadania przed uruchomieniem
1. Zaprojektować niezmienny rejestr **rzeczywistych** opłat platformy z unikalnym identyfikatorem źródła, czasem rozliczenia, korektami i identyfikatorem potwierdzonej płatności operatora.
2. Oddzielić przychody sprzedawców ze sprzedaży produktów, koszty dostawy i doładowania portfela od opłat należnych platformie.
3. Dopiąć rzeczywiste zdarzenia opłat za punkty odbioru, prowizji od wypłat i reklam, z ochroną przed ponownym naliczeniem.
4. Uzgodnić z księgowym zasady VAT, dat faktur, korekt, danych kontrahenta i KSeF; wdrożyć fakturowanie dopiero po zatwierdzeniu.
5. Przeprowadzić testy integracyjne z operatorem płatności i uzgodnienia grosz do grosza, następnie osobno autoryzować produkcję.

## Ostatni potwierdzony przebieg CI
Commit `9cf179d4`: Monthly platform accounting regression #128 — success; Approved UI and wallet ads regression #441 — success.

Gałąź robocza: `feat/zatwierdzony-widok-gwiazdki-reklamy-rls-20261118`.
Chronione pliki wyglądu: `web/index.html`, `web/style.css`, `web/app.js`.
