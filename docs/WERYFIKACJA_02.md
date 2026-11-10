# Weryfikacja 02 — audyt integralności danych

Dodano odczytowy audyt istniejącej bazy SQLite (`backend/data_integrity.py`). Sprawdza `PRAGMA integrity_check`, `PRAGMA foreign_key_check` i liczebność tabel. Nie zapisuje danych i nie tworzy nieistniejącej bazy.

Uruchomienie: `python -m backend.data_integrity /sciezka/do/bazy.sqlite`.
Kod wyjścia 0 oznacza brak wykrytych problemów, 1 — wykryte naruszenia. Raport może zawierać nazwy tabel i liczby rekordów; nie należy go publicznie udostępniać.

**PostgreSQL:** w tej wersji nie uruchomiono rzeczywistego serwera PostgreSQL, zatem nie można potwierdzić działania transakcji i blokad pod obciążeniem. Do wykonania pozostają testy integracyjne na odizolowanej instancji, w tym migracje, logowanie, zakup ostatniej sztuki, PIN, zwroty i wypłaty testowe.

To narzędzie nie zastępuje kopii zapasowej ani audytu bezpieczeństwa. Produkcyjne płatności pozostają wyłączone.
