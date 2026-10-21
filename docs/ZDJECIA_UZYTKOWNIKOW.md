# Zdjęcia użytkowników — obowiązujący wymóg

Uzgodnienie z użytkownikiem, 2026-10-21: każde zdjęcie dodawane przez
użytkownika ma być automatycznie kompresowane do maksymalnie **1 MB**.
Przyjmujemy limit **1 000 000 bajtów na pojedyncze zapisane zdjęcie**.
Dotyczy wszystkich miejsc dodawania zdjęć, w tym produktów, profili
i gospodarstw, niezależnie od urządzenia i roli użytkownika.

Wymagania dla implementacji modułu zdjęć:

- Kompresja jest automatyczna; użytkownik nie musi przygotowywać pliku ręcznie.
- Zachować proporcje i prawidłową orientację zdjęcia. W razie potrzeby
  zmniejszać rozdzielczość, aby uzyskać limit przy możliwie dobrej jakości.
- Ostateczny limit sprawdzać na serwerze po przetworzeniu. Nie polegać
  wyłącznie na JavaScript, rozszerzeniu pliku lub deklarowanym MIME.
- Każda ścieżka dodania lub zastąpienia zdjęcia musi używać wspólnej obsługi.
- Nie zapisywać oryginału większego niż limit jako opublikowanego zdjęcia.
  Jeśli przetworzenie się nie powiedzie, zwrócić czytelny błąd zamiast
  omijać limit lub usuwać poprzednie poprawne zdjęcie.
- Przed przetwarzaniem ograniczać rozmiar pliku źródłowego i liczbę pikseli;
  usuwać metadane EXIF, w tym lokalizację GPS, ze zdjęcia wynikowego.
- Sprawdzić m.in. duże zdjęcia telefonu, orientację, przezroczystość,
  błędny plik i wynik dokładnie na granicy limitu.

Stan początkowy: sam zapis wymagania. Poniżej opisano dodaną implementację testową; pozostaje domyślnie wyłączona.

## Implementacja testowa — 2026-10-21

Wspólny moduł `backend/user_photos.py` obsługuje dodanie, zastąpienie i usunięcie
zdjęcia produktu, profilu i gospodarstwa. Każdy cel ma jedno aktualne zdjęcie.
Flaga `WP_ENABLE_USER_PHOTOS=1` jest domyślnie wyłączona. PostgreSQL wymaga
osobnej, ręcznie sprawdzonej migracji `database/optional_user_photos.sql`.
Nie wdrożono na VPS.

Wejście: pojedynczy JPEG, PNG lub WebP, maksymalnie 20 000 000 bajtów i
50 mln pikseli; animacje i pozostałe formaty (w tym HEIC, GIF i SVG) są odrzucane.
Wyjście: JPEG do 1 000 000 bajtów, najdłuższy bok do 2048 px, zachowane
proporcje i orientacja EXIF. Przezroczystość jest składana na białym tle.
Nowy obraz RGB nie zawiera EXIF/GPS, XMP, ICC ani nazwy pliku źródłowego.
Oryginał nie jest zapisywany. Jednocześnie działa jeden dekoder w procesie.
Dane JPEG są w bazie; CHECK wymusza limit także poza kodem aplikacji.

Własność jest sprawdzana przed odbiorem i dekodowaniem pliku; sesja i własność
są ponownie sprawdzane w transakcji zapisującej wynik. Niepoprawny plik lub
utrata sesji nie zastępują poprzedniego poprawnego zdjęcia. Limit wejścia
jest sprawdzany także podczas strumieniowania bez Content-Length.

Panel „Twoje zdjęcia” informuje, że zdjęcia są publiczne. Rolnik zarządza
zdjęciem gospodarstwa i swoich produktów; zalogowany użytkownik — własnym
zdjęciem profilowym. Panel czyści pola po zmianie konta i odrzuca spóźnione
odpowiedzi. Zdjęcie produktu jest wyświetlane w katalogu; zdjęcia profilu i
gospodarstwa mają adres publiczny i podgląd właściciela w edytorze (brak nowej
osobnej strony publicznego profilu). Odśwież panel po dodaniu nowego produktu.
Zdjęcie można zastąpić lub usunąć. Przed produkcją należy uwzględnić zdjęcia
w pojemności i retencji kopii bazy oraz sprawdzić limity zasobów na VPS.

Testy: 15 lokalnych testów sanitizacji/HTTP (formaty, orientacja, metadane,
przezroczystość, szum, rozmiary, błędne pliki, animacja, role, sesja i twarda
granica bazy), 19 kontroli integracyjnych UI/schematu. Dodano test natywnego
PostgreSQL z restartem i dwa testy rzeczywistego file pickera w Chromium
(320/1280 px); ich wynik należy odczytać z nowego CI, nie z poprzedniej serii.

Dokumentacja Pillow: https://pillow.readthedocs.io/en/stable/reference/ImageOps.html

Pełna regresja lokalna 5d3652a / GitHub 3f4fbd3: 4253 passed, 0 failed, 81 skipped; 339/339 modułów; sources_unchanged=true we wszystkich częściach. Raporty w docs/audits/user_photos_2026-10-21/. Wyniki natywnego CI wymagają osobnego potwierdzenia.

Natywny CI 39648310801 dla 3f4fbd3: PostgreSQL 16 i 17 po 51/51, Windows
recovery 80/80. Raporty w native_3f4fbd3/. Poprawka oczekiwania w teście
Chromium toleruje chwilowo pusty edytor podczas odświeżania po usunięciu;
nie zmienia kodu aplikacji. Przeglądarka wymaga wyniku po tej poprawce.

Pełny Windows dla 25aa015: 4169 passed, 0 failed, 165 skipped (4334 łącznie),
bez błędnych, niekompletnych ani przekroczonych czasowo modułów. W tym samym
przebiegu 39649018368 Chromium przekroczył 600 s; nie zaliczono go.
Oddzielna diagnostyka wskazała zatrzymanie na Response.json() w teście po
otrzymaniu odpowiedzi PUT. Test teraz pobiera rzeczywisty zapisany JPEG
przez niezależne HTTP i sprawdza liczbę bajtów, zamiast metadanych odpowiedzi.
Kod aplikacji pozostał taki sam. Scenariusze zdjęć na 320/1280 px: 2/2,
0 błędów, 0 pominięć (diagnostyczny CI 39652429785, commit 4ab8e2e).
JUnit i podsumowanie zachowano w native_4ab8e2e/; nieudany przebieg w
native_25aa015/chromium-summary.json pozostaje zapisany, bez nadpisania.

Bramka browser uruchamia teraz zdjęcia osobno (limit 180 s), następnie
pozostałe 40 przypadków i kontrolę viewportów. Diagnostyka timeoutu publikuje
wyłącznie sprawdzoną nazwę pliku/funkcji testowej, bez stdout i parametrów.
39/39 lokalnych testów mechanizmu CI zaliczonych. Wynik całej nowej bramki
należy odczytać osobno; dedykowany workflow diagnostyczny nie jest częścią
kodu tej gałęzi.

## Wynik końcowej weryfikacji

Kod 1f96389 / GitHub 9538725: lokalnie 4254 passed, 0 failed, 81 skipped,
339/339 modułów, zgodny fingerprint we wszystkich częściach i
sources_unchanged=true. Raporty w final_9538725/.
CI 39652876736: zdjęcia Chromium 2/2 + pozostałe 40/40 + kontrola viewportów,
bez błędów i pominięć; PostgreSQL 16 i 17 po 51/51; Windows recovery 80/80.
Fingerprinty dowodów natywnych są zgodne. Raporty w native_9538725/.
Pełny Windows dla tego ostatniego zestawu testów nadal trwa w chwili zapisu;
nie jest mylony z wcześniej potwierdzonym 4169/0/165 dla identycznych plików
backend/web/database/zależności z 25aa015 (ostatnie zmiany dotyczą testów i CI).
Funkcja jest nadal domyślnie wyłączona i nie trafiła na VPS.
