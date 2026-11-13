# Paczka #60: osobne widoki, katalog po 20, oferty i punkty odbioru

Base: `codex/issue-59-pre-vps-20261113`
Head: `codex/issue-60-separate-views-20261113`
Refs #60.

Katalog jest samodzielnym widokiem z numerowanymi stronami po 20 produktów.
Koszyk, ulubione, zamówienia, portfel, konto i funkcje poszczególnych ról
mają osobne widoki sterowane URL. Działają wstecz/przód oraz ponowne
logowanie po odświeżeniu prywatnego URL; tokeny nadal pozostają w pamięci.
Publiczne filtry są zachowywane bez umieszczania współrzędnych w adresie.

Sprzedawca ma „Moje ogłoszenia”, szybką edycję ceny i wolnego stanu,
pełną edycję opisu/kategorii oraz dostęp do zdjęć. Kontrola `expected_stock`
chroni przed nadpisaniem rezerwacji przez stary formularz. Wycofanie jest
odwracalne i nie usuwa zapasu ani zamówień; nie zmienia też ich cen/jednostek.

„Punkty odbioru” obejmują istniejące formularze, mapę, terminy, opłaty,
promocje i nawigację. Współrzędne są ukrytymi polami. Usunięcie wymaga
potwierdzenia i nie jest możliwe przy aktywnych zamówieniach; zachowuje historię.

Walidacja: pełna regresja SQLite, natywny PostgreSQL, Chromium i pięć szerokości.
Dokładne wyniki: `docs/RAPORT_ISSUE_60_2026-11-13.md`.
Nowa addytywna migracja: `database/optional_product_listing_states.sql`
(46. pozycja manifestu). Zależności pozostają bez zmian.

Instrukcja PowerShell i plan kopii/migracji/rollbacku:
`docs/ISSUE_60_DEMO_I_VPS_2026-11-13.md`.
VPS, main i produkcyjne płatności pozostają nietknięte.
Fizyczny telefon i Windows wymagają ręcznego odbioru; publiczny Photon jest
blokowany w tej chmurze, a ogólna poczta wymaga osobnej konfiguracji testowej.
Hasła i dane fikcyjnych kont nie są publikowane.
