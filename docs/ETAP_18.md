# Etap 18 — marketplace jako pośrednik, a nie sprzedawca produktów

**Decyzja projektowa:** WiejskaPaka pośredniczy w sprzedaży, nie kupuje produktów od rolnika i nie odsprzedaje ich klientowi. Stroną umowy sprzedaży produktów jest sprzedawca, wskazany klientowi przed zakupem. WiejskaPaka świadczy odrębną usługę pośrednictwa, za którą pobiera prowizję.

- Faktury, paragony lub inne dokumenty sprzedaży produktów wystawia / zapewnia sprzedawca, jeżeli jest do tego zobowiązany. Nie każdy rolnik ma taki sam status podatkowy.
- Wyjątek istotny dla zakupów B2B: fakturę VAT RR wystawia czynny podatnik VAT nabywający produkty od rolnika ryczałtowego; nie oznacza to obowiązku platformy, jeżeli platforma nie jest nabywcą.
- Platforma dokumentuje **własną prowizję / usługę** zgodnie z właściwymi przepisami; nie należy mylić kwoty brutto wpłacanej przez klienta z przychodem platformy. Szczegóły podatkowe i przepływy środków wymagają księgowej i prawnej weryfikacji.
- Operator płatności marketplace powinien obsługiwać rozdzielenie środków i wypłaty sprzedawcom zgodnie z regulacjami; sama integracja płatności nie jest jeszcze wykonana.
- Dotychczasowe `invoice_drafts` to **wyłącznie nieemitowane projekty dotyczące prowizji**. Nie budujemy systemu wystawiania faktur w imieniu rolników.
- `GET /marketplace/accounting-policy` ujawnia zasady i status integracji bez danych osobowych.
- `backend.marketplace_policy.breakdown` oblicza rozdział groszowy wyłącznie informacyjnie. Opłata dostawy pozostaje w rozliczeniu sprzedawcy w tym uproszczonym modelu; rzeczywisty odbiorca opłaty zależy od umowy i wymaga osobnej ewidencji.

Przed produkcją: weryfikacja podatkowa, rozróżnienie rolnika ryczałtowego / VAT czynnego / innych sprzedawców, obowiązki ewidencyjne i konsumenckie, ustalenie właściwego operatora płatności, testy PostgreSQL.
