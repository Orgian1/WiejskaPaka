# Pakiet B/09 — kontrola gotowości demonstracji

Dodano `scripts/check_demo_readiness.py`, który uruchamia sprawdzanie w oddzielnym procesie z tymczasową bazą SQLite i usuniętymi zmiennymi PostgreSQL. Weryfikuje dostępność strony, znaczników mobilnych i paneli oraz plików JS/CSS. Następnie wykonuje istniejący scenariusz API odbioru i dostawy, w tym jednorazowego PIN-u i ograniczenia widoczności adresu kuriera.

Uruchomienie: `python -m scripts.check_demo_readiness` w katalogu projektu (po instalacji `requirements.txt`). Nie wymaga hostingu ani dostępu do internetu. Zakończenie kodem 0 oznacza pomyślne przejście automatycznych kontroli.

**Ograniczenia:** To nie jest test wizualny w przeglądarce ani test na fizycznym telefonie. Testy PostgreSQL/RLS nadal wymagają odizolowanego środowiska. Nie należy udostępniać demonstracji publicznie. Nie wprowadzono zmian do Neon, wiejskapaka.pl ani płatności.

Pełny lokalny zestaw: 2436 zaliczonych, 6 pominiętych, 16 podtestów zaliczonych.
