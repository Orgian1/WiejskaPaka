# Zależności gałęzi WiejskaPaka — 10.11.2026

Stan wejściowy: PR #50, commit ecd0c8d9163845ee86aaf4226d1be7c1deeeb533. Nowe prace bazują na tym commicie i pozostawiają wcześniejsze gałęzie bez zmian.

## Istotne ustalenia

- `main` (9b96de3) zawiera wyłącznie początkowy README i nie ma wspólnego przodka z historią aplikacji zaczynającą się w c5e1b49. Zmiana bazy PR #50 na main nie jest zwykłym scaleniem.
- Bieżąca aplikacja jest skumulowana na szczycie łańcucha. Zależności trzeba sprawdzać po SHA i przodkach, a nie tylko numerach PR.
- PR #10/#11 to starsza, rozbieżna ścieżka resetu. Aktualny łańcuch idzie przez #12 (v2). Późniejszy commit 30de9b8 zawiera kwarantannę przywróconej poczty. Nie doklejać automatycznie starej implementacji ani nie zamykać jej bez porównania.
- Pomiędzy #47 i #48 istnieje commit f692657 (`preview/wallet-interface-20261025`) bez osobnego otwartego PR na liście. Jest już w historii #48–#50.

## Bezpieczny wariant integracji

1. Zachować istniejący łańcuch i utworzyć gałąź `preview/demo-completion-20261110` z #50. Nowy PR ma bazę `fix/header-auth-links-20261109`, więc pokazuje tylko nowy pakiet.
2. Wykonać komplet testów na końcowym drzewie. Nie rebase'ować ani nie wykonywać force-push na starych gałęziach.
3. Wdrożenie demonstracyjne może wskazywać zatwierdzony SHA końcowego drzewa bez scalania kilkudziesięciu PR-ów i bez zmiany main.
4. Osobno przygotować scalanie od najstarszego przodka do szczytu. Przed każdym scaleniem ponownie sprawdzić aktualne SHA i czystość gałęzi. Samo `mergeable=true` nie dowodzi poprawności funkcjonalnej.
5. Ewentualne połączenie z main wykonać wyłącznie w osobnej gałęzi integracyjnej przez jawne połączenie rozłącznych historii; zachować README aplikacji i sprawdzić całe drzewo. Nie przepisywać main ani nie wykonywać reset --hard.

## Zachowana próba integracji

Gałąź `integration/demo-main-20261110` została zapisana na GitHubie jako
commit `3e9251301a598016b9b226619f88d43c6d9ba76e`. Ma dwóch rodziców: początkowy
main oraz przetestowany kod demo `90f9b5fbaacf792a995bf263e85f37b5dc09fbbe`.
Jej drzewo `f3c1b38c98822f2c99882a5e7949aa3645e55956` jest identyczne z kodem #51.
Nie przesuwa to main ani starych gałęzi. Ta gałąź nie uruchamia osobnego CI,
ponieważ filtr workflow obejmuje preview/** i wskazaną gałąź fix; dowodem
weryfikacji jest identyczne drzewo uruchomione w CI dla #51. Późniejszy raport
jest zapisywany na gałęzi #51 jako zmiana samych dokumentów.

## Otwarte PR-y odczytane z GitHuba

| PR | Gałąź zmian | Baza |
| --- | --- | --- |
| #10 | `preview/queued-reset-http-20261019` | `wiejskapaka-import` |
| #11 | `preview/reset-restore-quarantine-20261019` | `preview/queued-reset-http-20261019` |
| #12 | `preview/queued-reset-http-v2-20261019` | `wiejskapaka-import` |
| #13 | `preview/bounded-reset-worker-20261019` | `preview/queued-reset-http-v2-20261019` |
| #14 | `preview/reset-queue-retention-20261019` | `preview/bounded-reset-worker-20261019` |
| #15 | `preview/mail-key-backup-20261019` | `preview/reset-queue-retention-20261019` |
| #16 | `preview/mail-restore-quarantine-20261019` | `preview/mail-key-backup-20261019` |
| #17 | `preview/mail-configuration-check-20261019` | `preview/mail-restore-quarantine-20261019` |
| #18 | `preview/pg17-units-20261021` | `preview/mail-configuration-check-20261019` |
| #19 | `preview/fractional-quote-20261021` | `preview/pg17-units-20261021` |
| #20 | `preview/address-delivery-20261021` | `preview/fractional-quote-20261021` |
| #21 | `preview/user-photos-20261021` | `preview/address-delivery-20261021` |
| #22 | `preview/seller-search-20261021` | `preview/user-photos-20261021` |
| #23 | `preview/compact-account-20261021` | `preview/seller-search-20261021` |
| #24 | `preview/same-package-20261021` | `preview/compact-account-20261021` |
| #25 | `preview/combined-features-20261022` | `preview/same-package-20261021` |
| #26 | `preview/optional-preflight-20261024` | `preview/combined-features-20261022` |
| #27 | `preview/ses-order-mail-20261024` | `preview/optional-preflight-20261024` |
| #28 | `preview/account-email-proof-20261024` | `preview/ses-order-mail-20261024` |
| #29 | `preview/email-verification-http-20261024` | `preview/account-email-proof-20261024` |
| #30 | `preview/bounded-verification-checkout-mail-20261024` | `preview/email-verification-http-20261024` |
| #31 | `preview/bounded-order-confirmations-20261024` | `preview/bounded-verification-checkout-mail-20261024` |
| #32 | `preview/shared-mail-send-budget-20261024` | `preview/bounded-order-confirmations-20261024` |
| #33 | `preview/mail-suppression-core-20261024` | `preview/shared-mail-send-budget-20261024` |
| #34 | `preview/pinned-ses-feedback-20261025` | `preview/mail-suppression-core-20261024` |
| #35 | `preview/ses-feedback-trust-config-20261025` | `preview/pinned-ses-feedback-20261025` |
| #36 | `preview/encrypted-ses-review-20261025` | `preview/ses-feedback-trust-config-20261025` |
| #37 | `preview/ses-feedback-http-keys-20261025` | `preview/encrypted-ses-review-20261025` |
| #38 | `preview/retained-ses-key-check-20261025` | `preview/ses-feedback-http-keys-20261025` |
| #39 | `preview/ses-feedback-database-20261025` | `preview/retained-ses-key-check-20261025` |
| #40 | `preview/ses-feedback-service-preflight-20261025` | `preview/ses-feedback-database-20261025` |
| #41 | `preview/location-city-input-20261025` | `preview/ses-feedback-service-preflight-20261025` |
| #42 | `preview/two-account-panels-20261025` | `preview/location-city-input-20261025` |
| #43 | `preview/versioned-ui-assets-20261025` | `preview/two-account-panels-20261025` |
| #44 | `preview/pickup-calendar-seller-panel-20261025` | `preview/versioned-ui-assets-20261025` |
| #45 | `preview/product-photo-500kb-20261025` | `preview/pickup-calendar-seller-panel-20261025` |
| #46 | `preview/sns-subscription-confirmation-20261025` | `preview/product-photo-500kb-20261025` |
| #47 | `preview/verified-email-checkout-20261025` | `preview/sns-subscription-confirmation-20261025` |
| #48 | `preview/wallet-account-ledger-20261025` | `preview/wallet-interface-20261025` |
| #49 | `preview/wallet-integrity-check-20261026` | `preview/wallet-account-ledger-20261025` |
| #50 | `fix/header-auth-links-20261109` | `preview/wallet-integrity-check-20261026` |
| #51 | `preview/demo-completion-20261110` | `fix/header-auth-links-20261109` |

Nie wykonano scalania ani zamykania wcześniejszych PR-ów. Dokument nie potwierdza stanu VPS.


## Aktualizacja etapu 2 — portfel

PR #52: `preview/wallet-withdrawal-lifecycle-20261110`, baza
`preview/demo-completion-20261110`. Kod `36c8567` zawiera niezmienne warunki
wniosków i decyzje końcowe; wymaga nowej opcjonalnej migracji.
Próbna integracja z historią main ma teraz commit
`09d6aef0374a4392e0a15e0c2acb5a01e465b2b6`, z identycznym drzewem kodu #52.
Wcześniejszy zapis `3e92513` pozostaje jej przodkiem. Main i stare gałęzie PR-ów
pozostają bez zmian. Wyniki i zasady rollbacku: `WYPLATY_DEMO_ETAP2_2026-11-10.md`.

## Aktualizacja etapu 3 — połączenie czatu i Work

PR #53 ma bazę #52. Commit `5dedc0e` zachowuje pełny kod Work oraz trzy
nowe commity zwykłego czatu z gałęzi #50, zakończone `b9ca634`.
Obie historie są rodzicami scalenia; nie przepisywano żadnej wcześniejszej gałęzi.
Próbna integracja z main: `28c88591d63e849d511ea0bacda90b3d4bec9015`,
drzewo identyczne z `5dedc0e`. Main nadal wskazuje `9b96de3`.
Wyniki połączonego kodu: `INTEGRACJA_CZAT_WORK_2026-11-10.md`.
