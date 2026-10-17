# WiejskaPaka — integralność zwrotów i ponowień, 17.10.2026

Punkt wyjścia: `f99bcfecd7ebf5745d8c7aaa9ccd44f2690269a7`.
Gałąź lokalna: `wiejskapaka-import`. Szósta zbiorcza paczka napraw.

## Odtworzone problemy

Nowy zestaw przed poprawką: **12 FAIL, 7 PASS — 19 przypadków**.
To syntetyczne próby uszkodzonych rozliczeń, niezależne od historycznych
37 błędów lokalnej regresji Windows. Nie dowodzą wystąpienia takiego
uszkodzenia w rzeczywistych danych ani istnienia publicznej ścieżki do jego
wprowadzenia.

- Ponowienie anulowania przesyłki z zamkniętymi zamówieniami zwracało sukces
  i sumę zwrotów bez sprawdzenia stanów płatności. Mogło też przedstawiać
  zwykłe anulowanie nieopłaconej przesyłki jako wykonany zwrot płatności.
- Powtórzenia zwrotu nie zawsze odrzucały jednoczesny zapis zwrotu i wypłaty.
- Wewnętrznie spójna płatność mogła mieć inną kwotę niż zamówienie.
  Spójność samej symulacji nie wystarczała do bezpiecznego zwrotu.
- Niepoprawny zapis przy pierwszym zwrocie za winę dostawcy mógł powodować
  nieobsłużony błąd zamiast kontrolowanej odmowy 409.

## Zmiana

Wspólna kontrola w magazynie symulacji sprawdza stan i całkowite kwoty
płatności oraz porównuje jej identyfikator, kwotę produktów, dostawę i sumę
z zamówieniem. Sprawdza też poprawność sumy zamówienia. Nie korzysta z float.
Przy ponownym pobraniu istniejącej symulacji do zapisu kontrola działa przed
przetworzeniem zdarzenia płatności, również przed zwróceniem wyniku ponowienia.

Anulowanie pojedynczego zakupu, anulowanie przesyłki oraz zwrot za winę
dostawcy korzystają z kontroli przed pierwszym zwrotem i jego ponowieniem.
Niespójność daje ogólną odmowę 409; zapis pozostaje bez zmian.

Przesyłka częściowo opłacona nadal może być anulowana atomowo. Zwrot dotyczy
wyłącznie pozycji wcześniej opłaconych. Pozycje bez symulacji, oczekujące na
płatność i z nieudaną płatnością pozostają bez zwrotu. Potwierdzenie ponowienia
wymaga co najmniej jednego pełnego zwrotu i braku niedozwolonych stanów.
Ponowienie nie zwiększa zwrotu ani nie przywraca ponownie stanu magazynowego.

Nie dopisano automatycznej korekty pieniędzy, stanów ani zdarzeń. Nie zmieniono
kluczy ani schematu. Nie potwierdzano, że dowolnie uszkodzona historia zdarzeń
może być odtworzona; to nie jest narzędzie naprawy księgowej.

## Potwierdzone kontrole

- Paczka regresji: **50 PASS, 0 FAIL, 0 SKIP** w trzech modułach.
- Nowe próby obejmują pojedynczy zakup i przesyłkę, pierwszy zwrot i ponowienie,
  niezgodne sumy, częściowy zwrot, jednoczesną wypłatę, nieprawidłowy stan
  płatności, dostawę oraz ponowną rejestrację zdarzenia dla istniejącej symulacji.
- Trzy dodatnie przypadki sprawdzają przesyłkę częściowo opłaconą z pozycją
  bez płatności, oczekującą i z nieudaną płatnością. Pierwsze żądanie zwraca
  właściwą sumę, drugie tę samą sumę bez nowych zmian w bazie.
- Odrzucone próby porównują hash danych wszystkich tabel testowej bazy przed
  i po żądaniu. Testy działają przez ASGI TestClient na syntetycznych danych.

Procesy testowe nie otrzymują produkcyjnych sekretów ani adresów baz.
Używają jednorazowych SQLite i symulowanych płatności.

## Pełna regresja końcowa

**3522 PASS, 0 FAIL, 17 SKIP — 3539 przypadków, 280/280 modułów.**
Raport kompletny, `success: true`, `sources_unchanged: true`.
Przebieg wykonano od początku po ostatniej zmianie kodu i testów, bez wznowienia.
Odcisk źródeł: `0d545c7ff24b44cc3180a676f673ad687d021c5190456e56c24fb552bcb83c81`.

Osobna akceptacja rzeczywistego TCP HTTP: **4/4 zadania PASS**, także bez zmiany
źródeł. Obejmuje zakup, dostawę, pełny zwrot, koszyk wielu rolników, prywatność
oraz pojedynczą opłatę za przesyłkę. Nie sumujemy jej z przypadkami pytest.
Zestawienie bez surowych logów i lokalnych ścieżek:
[`audits/regression_2026-10-17_v6_summary.json`](audits/regression_2026-10-17_v6_summary.json).

Pominięcia: PostgreSQL 15 przypadków, mobilny test offline 1 i rozszerzony test
ról offline 1. Nie są zaliczeniami. Przyrost względem v5 wynika z 19 nowych
przypadków; nie oznacza wykonania historycznych lokalnych modułów Windows.
`git diff --check`: PASS.

## Pozostałe ograniczenia

Natywny Windows, PostgreSQL i Chromium pozostają do weryfikacji.
19 historycznych lokalnych modułów nie jest częścią repozytorium i nie zostało
tu uruchomionych. Testy nie zastępują pełnego audytu bezpieczeństwa, RLS,
zgodności konsumenckiej, wydajności oraz sprawdzonych kopii i odtwarzania.
Ta kontrola nie potwierdza integralności dowolnie zmienionej historii zdarzeń
ani możliwości odtworzenia brakującej płatności. Uszkodzenia wymagają analizy.
Kod współdzielony obejmuje PostgreSQL, ale nie dowodzi jego natywnego działania.
Aplikacja nadal nie jest gotowa do wdrożenia produkcyjnego.

Zachowano całkowite grosze, opłatę raz na przesyłkę, PIN, pełny zwrot przy winie
dostawcy i prywatność telefonów. Nie podłączano domeny, hostingu ani operatora
płatności. `main` pozostaje bez zmian.

Ponowny odczyt gałęzi GitHub potwierdził bazę
`c5e1b49d337b8641eec2933321d750017b788168`. Zapis integracji pozostaje
niepotwierdzony po wcześniejszym 403; nie ponawiano go bez nowych uprawnień.
Lokalne poprawki przekazano w zbiorczym bundle i patchu.
