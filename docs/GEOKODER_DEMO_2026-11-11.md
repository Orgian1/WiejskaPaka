# Wyszukiwanie nowych adresów w lokalnym demo

Kontynuacja PR #57, bez zmian danych VPS. Moduł Nominatim istniał wcześniej,
ale launcher usuwał odziedziczoną konfigurację geokodera. Nowa opcja
`--address-search-url` jawnie włącza go tylko w procesie serwera demo.
Przygotowanie przykładowych kont nadal działa bez usług zewnętrznych.
Bez tej opcji demo nadal wyszukuje zapisane punkty odbioru.

## Uruchomienie

Z katalogu aktualnego projektu w PowerShell:

```powershell
$geocoderUrl = Read-Host 'Adres HTTPS własnej lub zakontraktowanej usługi Nominatim (endpoint search)'
.\.venv\Scripts\python.exe scripts/run_phone_demo.py --full-demo --address-search-url $geocoderUrl
```

Wymagany jest działający endpoint zgodny z Nominatim, obsługujący zapytania
strukturalne city/street/postalcode i format jsonv2. Nie ma domyślnego dostawcy.
Adres URL nie może zawierać loginu, hasła, parametrów, fragmentu ani znaków
sterujących. Publiczny serwer openstreetmap.org pozostaje wyłączony zgodnie
z dotychczasowymi zasadami projektu. Integracja nie obsługuje kluczy API.

Po kliknięciu Szukaj wpisany adres jest przesyłany do skonfigurowanej usługi.
Użytkownik wybiera wynik; nie ma automatycznego wyboru pierwszego kandydata.
Włączenie konfiguracji nie potwierdza dostępności dostawcy. Błąd połączenia
jest prezentowany przez istniejący komunikat wyszukiwarki.

Demo pozostaje na 127.0.0.1:8765 i jednorazowej bazie SQLite. Jego dane
znikają po zakończeniu procesu. Ten launcher nie jest procedurą wdrożenia VPS.
Poczta, PayU i zewnętrzna baza nie są dziedziczone z otoczenia.

## Weryfikacja 11 listopada 2026

Python 3.12, zależności z requirements-lock.txt:

```text
python -m pytest -q tests/test_address_search.py tests/test_local_address_search.py tests/test_address_search_ui.py tests/test_phone_demo_launcher.py tests/test_sample_demo_launcher.py tests/test_full_local_demo.py tests/test_purchase_record_http_restart.py
54 passed, 0 failed (13.28 s)
```

Zakres: adapter z atrapą dostawcy, walidacja konfiguracji, skrypt UI,
izolacja launchera, tworzenie pełnego demo i rzeczywisty lokalny HTTP
z geokoderem włączonym i wyłączonym, regresja restartu zapisów zakupowych.
Pierwszy przebieg wykazał brak jawnego przekazania geokodera w pomocniku
serwera testowego, który również izoluje środowisko. Poprawiono pomocnik
i ponowiono cały powyższy zestaw. Ostrzeżenie zależności: Starlette zapowiada
wycofanie httpx w TestClient; nie zmieniano zależności projektu.

Nie wykonano połączenia z rzeczywistym geokoderem, testu fizycznego GPS,
nowego pełnego zestawu Windows ani wdrożenia VPS. Do odbioru nowych adresów
potrzebny jest adres rzeczywiście dostępnej usługi geokodowania.
