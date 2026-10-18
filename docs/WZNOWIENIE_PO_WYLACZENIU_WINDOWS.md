# Wznowienie demo po wyłączeniu komputera — Windows

Kod aplikacji jest zapisany na gałęzi GitHub `wiejskapaka-import`.
Okna przeglądarki i terminala nie są kopią projektu. GitHub Actions działa
na maszynach GitHuba, niezależnie od włączenia Twojego komputera. Lokalny
serwer demo przestaje działać po jego wyłączeniu.

## Pobranie świeżej kopii bez nadpisywania starego katalogu

W PowerShell, w katalogu przeznaczonym na projekty. Potrzebne Git i Python
3.12. Poniższa nazwa katalogu musi jeszcze nie istnieć; w przeciwnym razie
wybierz inną nową nazwę. Zachowaj stary katalog do sprawdzenia własnych zmian.

```powershell
git clone --branch wiejskapaka-import --single-branch https://github.com/Orgian1/WiejskaPaka.git WiejskaPaka-demo-nowy
Set-Location .\WiejskaPaka-demo-nowy
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\run_phone_demo.py --sample-data
```

Otwórz adres pokazany w terminalu, zwykle `http://127.0.0.1:8765`.
Nie zamykaj terminala podczas używania demo. Nie trzeba aktywować środowiska
PowerShellem ani zmieniać polityki wykonywania skryptów. Gdy terminal zgłosi
błąd, nie przechodź do kolejnego kroku; zachowaj sam komunikat bez haseł.

Serwer wypisze cztery nowe fikcyjne konta i oddzielne losowe hasła. Przy
logowaniu rola jest rozpoznawana z konta — selektor roli dotyczy rejestracji.
Adres jest dostępny tylko na komputerze uruchamiającym serwer; to nie jest
podłączenie domeny ani podgląd na innym telefonie.

Jeśli port jest zajęty, zakończ tę próbę i użyj:

```powershell
.\.venv\Scripts\python.exe scripts\run_phone_demo.py --sample-data --port 8766
```

## Co zostaje, a co jest jednorazowe

- Zapisane commity, kod, instrukcje i oczyszczone raporty pozostają w GitHubie.
- Każdy start z `--sample-data` tworzy nową bazę, klucz i zestaw kont.
  Hasła z poprzedniego uruchomienia nie służą do logowania do nowego demo.
- Odświeżenie strony usuwa token z pamięci strony. Nie usuwa przy tym
  zakupów z nadal działającego serwera — zaloguj się ponownie bieżącym kontem.
- Ctrl+C kończy demo i sprząta jego katalog. Po nagłym wyłączeniu komputera
  sprzątanie może nie nastąpić. Nie używaj odnalezionego katalogu tymczasowego
  jako zaufanej bazy produkcyjnej ani nie dołączaj jego plików do GitHuba.
- Kod i kopia bazy to różne rzeczy. Narzędzia kopii opisuje
  `ODTWARZANIE_SQLITE.md`. Nie kopiuj losowego nowego klucza do starej bazy.

## Gdzie sprawdzić postęp

Bieżący pakiet zgłoszeń opisuje `RAPORT_ZGLOSZEN_2026-10-18.md`.
Przebiegi: https://github.com/Orgian1/WiejskaPaka/actions

Pełny Windows, szybki Windows, PostgreSQL i Chromium to osobne zadania.
Zaliczenie szybkiego Windows nie oznacza ukończenia pełnego. Raport zawsze
wskazuje badany commit. Dokumentacyjny commit z `[skip ci]` nie zmienia kodu
aplikacji i nie jest nowym wynikiem testów.

Scenariusz wszystkich ról: `DEMO_Z_DANYMI.md`. Nowe zgłoszenia problemów:
`ZGLOSZENIA_PROBLEMOW_TESTOWE.md`. Nie wpisuj prawdziwych danych, haseł innych
usług ani danych rachunku do tego demonstracyjnego środowiska.
