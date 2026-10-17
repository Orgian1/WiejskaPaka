# Pakiet B/08 — lokalny podgląd interfejsu

Nowy skrypt `scripts/run_phone_demo.py` uruchamia istniejący interfejs `web/` i API FastAPI w jednym procesie serwera, z nową tymczasową bazą SQLite.

## Uruchomienie

```bash
python -m pip install -r requirements.txt
python scripts/run_phone_demo.py
```

Otwórz `http://127.0.0.1:8765` **na tym samym urządzeniu**, na którym działa Python. Możesz zmienić port: `--port 8766`. Aby zakończyć: Ctrl+C. Dane demonstracyjne znikają po zakończeniu. Skrypt nie zakłada kont testowych automatycznie — można je utworzyć w interfejsie.

**Ograniczenie:** to nie jest publiczny adres ani automatycznie dostępny podgląd z osobnego telefonu. Serwer nasłuchuje wyłącznie na `127.0.0.1` celowo, aby nie udostępniać niedokończonej aplikacji w sieci. Do ręcznych testów na fizycznym telefonie konieczne będzie osobne, kontrolowane środowisko testowe.

Skrypt usuwa zmienne konfiguracyjne PostgreSQL i Neon z procesu potomnego. Nie włącza płatności ani nie modyfikuje strony wiejskapaka.pl. Nie jest rozwiązaniem do wdrożenia produkcyjnego.

## Sprawdzenie

Dodano trzy testy automatyczne: izolacja konfiguracji, wymuszenie nasłuchiwania wyłącznie lokalnego oraz odpowiedź strony i zasobów JS/CSS. Pełny zestaw lokalny: 2433 zaliczone, 6 pominiętych, 16 podtestów zaliczonych. Nie przeprowadzono rzeczywistych testów na fizycznym telefonie ani na PostgreSQL.
