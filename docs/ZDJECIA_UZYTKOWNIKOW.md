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
