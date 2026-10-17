# B/1801–B/1860 — testy równoczesnych zakupów

Dodano `tests/test_b1801_concurrent_stock.py` z dwoma rzeczywistymi scenariuszami HTTP wykonywanymi równocześnie na osobnych klientach FastAPI i wspólnej testowej bazie SQLite:

1. Dwóch klientów próbuje kupić ostatnią sztukę produktu. Dokładnie jeden zakup musi się udać, stan magazynowy nie może spaść poniżej zera, a baza musi zawierać tylko jedną przesyłkę.
2. Ten sam klient równocześnie ponawia zakup z tym samym `Idempotency-Key`. Oba żądania muszą zwrócić identyczny wynik, z jedną przesyłką i jednym odjęciem magazynu.

Weryfikowana jest także opłata za dostawę naliczona tylko raz na przesyłkę. Nie modyfikowano konfiguracji Neon, produkcyjnych płatności ani domeny. Testy te nie zastępują testów równoległości na PostgreSQL ani pełnej regresji.
