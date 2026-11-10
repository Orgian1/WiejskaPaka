# WiejskaPaka — końcowy odbiór wersji demonstracyjnej

**Stan: gotowa do końcowej kontroli lokalnej bez prawdziwych płatności.**
Wdrożenie na VPS wymaga jeszcze odczytu jego aktualnego stanu, zabezpieczenia
danych i próby odtworzenia. W tej sesji nie wykonywano tych operacji na VPS.

## Wersja do kontroli

Gałąź: `preview/demo-environment-isolation-20261110`, PR #54.
Przetestowany kod: `064ab859412015f0f6d58fc2fb059d75ec8d47ed`.
Późniejsze commity tej gałęzi uzupełniają wyłącznie dokumentację i dowody.
Nie zmieniono main ani wcześniejszych gałęzi użytkownika.

| Pakiet | Zawartość |
| --- | --- |
| #51 | pełny profil lokalnego demo, prowizja 5%/0%, kontrola historii salda |
| #52 | niezmienne warunki wypłat, anulowanie i zakończenie symulacji |
| #53 | bezpieczne odzyskanie operacji po utracie odpowiedzi; połączenie trzech nowych commitów zwykłego czatu z #50 |
| #54 | izolacja wszystkich trybów demo od sekretów i ustawień usług zewnętrznych |

Przygotowane połączenie z historią main:
`integration/demo-main-20261110`, `f2d27a89626f341d32e366a50b30c36ecbf65cc2`.
Jego drzewo jest identyczne z testowanym kodem `064ab85`; dokumentacja jest
uzupełniana na gałęzi #54. Nie jest to wdrożenie ani przesunięcie main.

## Wyniki rzeczywistych testów

Końcowy przebieg: https://github.com/Orgian1/WiejskaPaka/actions/runs/42805536971.
**Wszystkie 5 zadań zakończone sukcesem.**

| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełny Windows | 4642 | 0 | 275 |
| Szybki Windows | 91 | 0 | 0 |
| PostgreSQL 16 | 97 | 0 | 0 |
| PostgreSQL 17 | 97 | 0 | 0 |
| Chromium | 76 | 0 | 0 |

Windows obejmuje 4917 przypadków, bez timeoutów i niekompletnych modułów.
Chromium dodatkowo sprawdził HTTP przy pięciu rozmiarach widoku.
Nie sumować zestawów: częściowo uruchamiają te same przypadki. Pominięcia
nie są zaliczeniami. Raporty i odciski źródeł:
`audits/demo_environment_isolation_2026-11-10/`.

Pełny lokalny Linux: 4756 PASS, 61 FAIL, 100 SKIP, zakończone 387/387 modułów.
Wszystkie 61 błędów dotyczą blokady socketu AF_UNIX przy starcie Chromium.
Ten przebieg nie jest pełnym sukcesem; testy Chromium wykonano w CI.

Dodatkowy odbiór bieżącej wersji: 18 PASS, 0 FAIL, 0 SKIP — gotowość strony,
izolowana ścieżka zakupu, nagłówek, pełny profil i przygotowanie danych demo.
Manifest 40 plików SQL oraz sumy kontrolne są zgodne. Kontrola manifestu
nie wykonuje migracji. Dowody: `audits/final_acceptance_2026-11-10/`.

## Uruchomienie i kontrola właściciela

Z katalogu projektu, Python 3.12, Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo
```

Otworzyć http://127.0.0.1:8765. Terminal pokaże nowe losowe konta klienta,
sprzedawcy, dostawcy i administratora. Ctrl+C kończy demo i usuwa jego bazę.
Dotychczasowe dane użytkownika nie są otwierane ani zmieniane.
Scenariusz każdej roli, PIN-y, portfel i panel administratora:
`DEMO_BEZ_PAYU_2026-11-10.md`. Nie używać rzeczywistych haseł ani środków.

Odbiór obejmuje rejestrację i logowanie, katalog i koszyk, punkty i terminy,
dostawę, jedną opłatę za przesyłkę, jednorazowy PIN, prywatność adresu,
zwroty, raporty i zgłoszenia. W portfelu: grosze, 5% dla wypłat sprzedawcy,
0% dla klienta, anulowanie, zamknięcie przez admina oraz odzyskanie operacji.
Testy syntetyczne powiadomień nie oznaczają wysyłki rzeczywistego e-maila.

## Pozostałe granice

- VPS: brak zweryfikowanego dostępu i bieżącego odczytu. Przed zmianą wykonać
  procedurę `WDROZENIE_I_WYCOFANIE_DEMO_2026-11-10.md`, w tym kopię i próbę
  odtworzenia. Zachować niezacommitowane zmiany i klucze; nie używać reset --hard.
- Fizyczny telefon: automatyczne testy obejmują rozmiary mobilne i desktopowe.
  Dostęp z osobnego telefonu wymaga zabezpieczonego podglądu; lokalny launcher
  pozostaje na 127.0.0.1. Nie deklarujemy odbioru na fizycznym urządzeniu.
- Portfel i płatności zamówień są osobnymi symulacjami. Portfel nie opłaca
  zamówień i nie otrzymuje ich zwrotów; nie dodawać obu sald ani prowizji.
- Zakup obsługuje całkowite ilości jednostek. Ułamkowy zakup nie jest częścią
  bieżącego przepływu; zachowano wcześniejszy osobny moduł wyceny ułamkowej.
- Nie podłączano PayU, banku ani prawdziwych płatności. Wysyłka poczty przez
  rzeczywistą usługę i jej obecna konfiguracja wymagają odrębnego odbioru.

Nie ma dodatkowego etapu wdrożenia możliwego w tej sesji bez dostępu do VPS.
Kod demo, automatyczne testy, instrukcja i plan wycofania są zapisane na GitHubie.
