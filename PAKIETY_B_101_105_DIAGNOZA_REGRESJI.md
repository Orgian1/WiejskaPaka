# B/101–B/105 — diagnostyka regresji

- B/101: sprawdzono zachowanie podziału plików testowych na partie.
- B/102: dodano `--start-batch N`, aby wznawiać od konkretnej partii bez ponownego uruchamiania poprzednich.
- B/103: dodano `--stop-on-failure` dla szybkiej lokalizacji błędów i zapisywania raportu.
- B/104: walidacja numeru pierwszej partii.
- B/105: testy odmowy uruchomienia pustej listy plików.

## Diagnoza

Pierwsze trzy partie po 24 pliki testowe zakończyły się sukcesem (15,74 s; 5,97 s; 10,19 s). Czwarta partia przekroczyła ustawiony limit 12 s. Przy osobnym uruchomieniu podzbioru testów bez izolowanej bazy wystąpił konflikt rejestracji użytkownika (HTTP 409) w `test_stabilization_02.py`. To dowodzi konieczności korzystania z `scripts/run_tests_isolated.py` lub nowego runnera, ale nie jest jeszcze dowodem defektu aplikacji. Nie potwierdzono pełnej regresji.

Przykład: `python scripts/run_regression_chunks.py --batch-size 12 --timeout 90 --start-batch 4 --stop-on-failure --report raport.json`

Nie łączono się z Neon ani nie uruchamiano płatności produkcyjnych.
