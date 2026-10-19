# Pozostałe prace — stan 19.10.2026

Cel najbliższego etapu: trwały prywatny podgląd WiejskiejPaki na opłaconym
serwerze, na sztucznych danych i bez rzeczywistych płatności. Domena już jest.
Serwer i poczta oczekują na aktywację. Nie jest to otwarcie publicznej sprzedaży.

## Zamknięty zakres funkcjonalny — nie budować ponownie

Zaimplementowano atomowe wystawienie tokenu i zaszyfrowanego zadania resetu,
testowe HTTP SQLite/PostgreSQL, dzierżawy z trwałym rozpoczęciem próby,
ograniczone ponowienia, obsługę niepewnej wysyłki, ograniczony proces roboczy,
retencję, osobną kopię kluczy i kwarantannę kolejki po odtworzeniu bazy.
Adapter SMTP i lokalna kontrola konfiguracji są przygotowane. Wysyłka
rzeczywista nadal nie jest podłączona. Szczegóły dowodów są w checkpointach;
wynik jednego commita nie jest wynikiem kolejnej zmiany.

## Kolejność dalszych prac

| Zadanie | Co jest przygotowane | Warunek zamknięcia |
| --- | --- | --- |
| Odbiór ostatniego pakietu | Testy kontrolne; uruchomiona pełna regresja Linux i CI | Zweryfikowane raporty dla badanego commita |
| Prywatny podgląd na VPS | Szablon jednostki, manifest SQL, ograniczona rola API, preflight i tunel SSH | Faktyczny start, kontrola uprawnień i trwałość po restarcie na zakupionym serwerze |
| Konfiguracja i próba poczty | Adapter TLS, kolejka i lokalny walidator | Parametry dostawcy, poprawne DNS i odebrana własna wiadomość próbna |
| Uruchamianie pracownika | Ograniczony proces i trwały rejestr prób | Oddzielne konto, minimalne prawa bazy, launcher/nadzorca i test przerwania usługi |
| Kopie na serwerze | Narzędzia szyfrowania i próby odtwarzania SQLite/PostgreSQL | Spójna procedura operatora dla bazy i kluczy, kopia poza VPS i faktyczny odbiór odtworzenia |

Instrukcja podłączenia: PODLACZENIE_SERWERA_I_POCZTY_2026-10-20.md.
Pierwszy prywatny podgląd przez SSH można odebrać niezależnie od wysyłki
poczty i bez zmieniania publicznych rekordów domeny.

## Osobny zakres przed publicznymi użytkownikami

- Potwierdzanie adresów e-mail i odbiór całego przepływu wiadomości.
- Publiczny HTTPS, kontrola konfiguracji domeny i izolacji środowisk.
- Weryfikacja procedur bezpieczeństwa, dokumentów i obsługi użytkowników.
- Pomiar wydajności dla uzgodnionego ruchu, monitoring i obsługa awarii.
- Osobny odbiór operatora płatności; brak kluczy PSP w podglądzie.

Te punkty nie blokują technicznego uruchomienia zamkniętego podglądu na
sztucznych danych. Nie podawać procentu ukończenia ani terminu publicznego
startu wyłącznie na podstawie liczby zaliczonych testów. Historyczny błąd
checkoutu Windows pozostaje niewyjaśniony: nowszy kod przeszedł pełny Windows,
a druga próba starego przebiegu zakończyła się startup_failure bez zadań.
Nie oznaczać go jako naprawionego ani losowego bez dalszego dowodu.
