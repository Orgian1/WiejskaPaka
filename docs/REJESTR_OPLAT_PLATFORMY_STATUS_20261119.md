# WiejskaPaka — rejestr opłat platformy (19.11.2026)

## Zakres gotowy w gałęzi roboczej
- Osobna tabela `platform_fee_ledger`, bez migracji sald portfeli i bez zmiany zatwierdzonego interfejsu.
- Rodzaje opłat: `pickup_point`, `seller_withdrawal_fee`, `advertising`.
- Zapis kwot jako całkowite grosze w PLN, unikalne `source_id`, identyfikator sprzedawcy, data operacji, opcjonalne źródło operatora.
- Zapisy są niemodyfikowalne i nieusuwalne przez zwykłe UPDATE/DELETE; korekty są oddzielnymi zdarzeniami z odwołaniem do pierwotnej opłaty.
- Ujemne korekty nie mogą łącznie przekroczyć pierwotnej opłaty; nie mogą odnosić się do innego sprzedawcy, rodzaju opłaty ani do innej korekty.
- Miesięczny odczyt i wewnętrzny raport roboczy, z kontrolą sum i odrębnymi pozycjami dla sprzedawców.
- Raport jest oznaczony `draft_unverified`, `fiscal_document=False`, `payment_provider_confirmed=False`.
- Automatyczne testy księgowe uruchamiane przez GitHub Actions; osobna kontrola zatwierdzonego interfejsu.

## Granice gotowości
**Ten moduł nie jest podłączony do produkcyjnego procesu pobierania opłat.** Nie potwierdza wpływu środków, nie wystawia faktur i nie rozlicza podatku. Nie wolno przedstawiać danych roboczych jako opłaconych transakcji. Testowy adapter wypłat również nie jest dowodem transferu bankowego.

## Przed uruchomieniem produkcyjnym
1. Powiązać zapis opłaty z wiarygodnym zdarzeniem biznesowym, płatnością lub rozliczeniem operatora; zapewnić idempotencję na poziomie całego procesu.
2. Zdefiniować datę powstania opłaty, datę świadczenia, zwroty, rabaty i okresy 30-dniowe (w tym promocje bezpłatnych punktów).
3. Uzgodnić przepływ pieniędzy, model portfela, prowizję sprzedawcy 5%, obsługę nieudanych wypłat i uzgodnienie z PayU.
4. Zweryfikować wymogi podatkowe, terminy fakturowania, VAT i KSeF z księgowym; dopiero potem włączyć osobny moduł dokumentów podatkowych.
5. Przetestować scenariusze równoległych zapisów i odtwarzanie kopii zapasowej oraz kontrolę uprawnień dostępu do bazy.
6. Przeprowadzić testy end-to-end na zatwierdzonym interfejsie, bez zmiany chronionych plików `web/index.html`, `web/style.css`, `web/app.js`.

## Zasada wdrożenia
Brak aktywacji płatności rzeczywistych, automatycznego wystawiania faktur, zmian w saldach, wdrożenia na serwer lub scalania do `main` bez osobnego zatwierdzenia.
