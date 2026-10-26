# Kontrola zgodności portfela z dziennikiem

Poprzednia wersja portfela 16cbcfbe, run 40230392540: Chromium, PostgreSQL 16/17, windows_recovery i pełny Windows zakończyły się SUCCESS. Ten wynik nie zastępuje CI poniższej zmiany.

Nowy backend.wallet_integrity oblicza uznania i rezerwacje z dziennika jednym zapytaniem SELECT. Sprawdza dostępne saldo, rezerwę, liczbę i ciągłość rewizji oraz końcowe salda ostatniego wpisu. Dotyczy obecnych dwóch operacji prywatnego podglądu: topup/credited i withdrawal/pending. Przy dodawaniu rozliczenia/odrzucenia wypłaty, zakupów, zwrotów lub przychodów sprzedawcy model uzgodnienia musi zostać rozszerzony o nowe rodzaje operacji.

Doładowanie i rezerwacja wypłaty sprawdzają spójność po zablokowaniu wiersza konta, w tej samej autoryzowanej transakcji. Rozbieżność daje HTTP 409 bez nowego wpisu, kredytu lub rezerwy. Kontrola nie naprawia automatycznie danych, nie uznaje wpłat od operatora i nie potwierdza rzeczywistych środków.

Operator może wywołać python -m scripts.check_wallet_integrity --check z nowego wydania, jako użytkownik aplikacji i z chronionym preview.env. Bez --check skrypt niczego nie otwiera. Z --check akceptuje jedynie dedykowany lokalny PostgreSQL i nieuprzywilejowaną rolę aplikacji. Połączenie jest read-only, timeout połączenia 5 s, zapytania 10 s. Nie importuje głównej aplikacji, nie uruchamia HTTP, SMTP ani migracji. Limit 10 000 portfeli; przekroczenie nie jest raportowane jako pełne pomyślne sprawdzenie.

Raport zawiera status, liczbę portfeli i wpisów oraz stałe kody błędów. Bez identyfikatorów właścicieli, sald, haseł, PIN-ów i szczegółów połączenia. WALLETS_VALID potwierdza zgodność matematyczną obecnego dziennika, a nie pokrycie salda rzeczywistymi wpłatami lub odporność na celowe przepisanie całej bazy.

Walidacja lokalna: 16 testów przeszło, w tym rzeczywisty HTTP, trwałość, równoległe wypłaty, idempotencja, wykrycie celowych zmian salda/dziennika i blokada kolejnych zapisów bez zmian środków. Dodano natywny test PostgreSQL; lokalna kolekcja 77 testów w module native. Wykonanie PostgreSQL i pełnej regresji wymaga CI nowej zmiany. Nie zmieniono VPS ani schematu bazy.
