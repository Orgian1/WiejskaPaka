# WiejskaPaka — lokalne demo na Windows

1. Zainstaluj **Python 3.12 (64-bit)** z python.org. Zaznacz „Add python.exe to PATH”. Node i PostgreSQL nie są potrzebne do ręcznego demo.
2. Rozpakuj cały ZIP do nowego katalogu, np. `C:\WiejskaPaka-DEMO`. Nie nakładaj go na poprzednią wersję.
3. Kliknij dwukrotnie **START_DEMO_WINDOWS.cmd**. Pierwszy start pobierze zależności z internetu; poczekaj na komunikat `WiejskaPaka DEMO`.
4. Otwórz **http://127.0.0.1:8765**. Nie zamykaj okna uruchomienia.
5. W oknie zobaczysz cztery fikcyjne adresy e-mail i losowe hasła: klienta, rolnika, dostawcy i administratora. Skopiuj odpowiednią parę do formularza logowania. Nie publikuj tych danych.

Każde uruchomienie tworzy nową bazę SQLite oraz fikcyjne konta, dwa produkty, przesyłkę do odbioru i dostawę w drodze. Wszystkie płatności i wypłaty są testowe. Nie podawaj prawdziwych danych. Nie jest wymagane połączenie z VPS, PayU ani produkcyjną bazą.

## Co sprawdzić

- **Klient:** katalog, wyszukiwanie, „Blisko mnie” (lokalizacja Legnica), ulubione, koszyk, zakup, płatność testowa, lista zamówień, odzyskanie PIN-u i portfel.
- **Rolnik:** ogłoszenia, cena i magazyn, punkty odbioru, zamówienia, decyzja o dostawie i odbiór PIN-em. PIN skopiuj wcześniej jako klient.
- **Klient po odbiorze:** wystaw ocenę sprzedawcy, sprawdź jej zapis po odświeżeniu; druga inna ocena tego zamówienia powinna zostać odrzucona.
- **Portfel:** sprawdź saldo oraz testowe operacje, w tym podgląd prowizji sprzedawcy.
- **Administrator:** przegląd sprzedawców, raporty, zgłoszenia i kampanie reklamowe. Dodaj fikcyjny baner z terminem obejmującym dzisiaj. Przy wejściu klienta lub rolnika do portfela reklama trwa 5 sekund i znika sama; ponowne wejście przed upływem 30 minut nie powinno jej pokazywać. Brak kampanii nie powinien blokować portfela.
- **Dostawca:** dostawa testowa i potwierdzenie PIN-em; po zakończeniu adres klienta powinien przestać być dostępny.

Szczegółowe scenariusze są w `docs/DEMO_Z_DANYMI.md`. Informacja o „sprawdzeniu towaru” w tym starszym dokumencie może różnić się od bieżącego interfejsu.

## Zakończenie i problemy

**Ctrl+C** w oknie kończy demo. Dane próbne zostają usunięte. Następny start utworzy inne konta i hasła. Kod aplikacji pozostaje w rozpakowanym katalogu.

Jeśli port 8765 jest zajęty, otwórz terminal w katalogu projektu i wykonaj:

```powershell
.\.venv-demo\Scripts\python.exe scripts\run_phone_demo.py --full-demo --port 8766
```

Wtedy wejdź na http://127.0.0.1:8766. Przy błędzie instalacji lub startu zachowaj treść błędu. Nie przesyłaj haseł, PIN-ów ani całego okna z kontami demo.

To paczka do lokalnego testowania. Status faktycznie wykonanych testów i ograniczenia są w `WYNIKI_WERYFIKACJI_20261116.md`; samo przygotowanie paczki nie oznacza, że wszystkie kontrole przeszły.
