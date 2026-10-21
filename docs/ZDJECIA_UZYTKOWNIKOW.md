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

Stan: to zapis wymagania. Obecny kod nie ma jeszcze modułu przesyłania
zdjęć; automatyczna kompresja i serwerowa kontrola nie są jeszcze wdrożone.
