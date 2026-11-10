# WiejskaPaka — zbiorczy pakiet 28–32

## Zrealizowane
- Nowy moduł `backend/verified_writes.py`: ponowne sprawdzenie tokenu i roli w **tej samej transakcji PostgreSQL**, w której wykonywany jest zapis.
- Wpięcie do pięciu tras zmieniających zamówienia: utworzenie zamówienia, potwierdzenie PIN, przygotowanie odbioru, przypisanie kuriera, rozpoczęcie dostawy.
- Sprawdzenie, że identyfikator i rola ponownie zweryfikowanej sesji zgadzają się z aktorem ustalonym na początku żądania. Brak możliwości wyboru aktora przez treść żądania.
- SQLite zachowuje dotychczasowy przepływ testowy.
- Testy modułu sprawdzają prawidłowy zapis, zmianę aktora, zmianę roli i błąd bazy.

## Granice bezpieczeństwa
- To **nie jest pełne zabezpieczenie wszystkich zapisów**: pozostałe trasy API wymagają przeglądu i migracji.
- Nie wdrożono ani nie włączono RLS. Konto współdzielone z bazą pozostaje wrażliwym elementem architektury.
- Nie przeprowadzono połączenia z rzeczywistym Neon; wymagane testy integracyjne z izolowaną bazą PostgreSQL.
- Nie wykonano wdrożenia ani integracji prawdziwych płatności.
- Tryb testowy potwierdzenia odbioru nadal ufa deklaracji `checked_goods` przesłanej przez uprawnionego operatora; docelowy proces potwierdzania przez kupującego wymaga osobnego projektu.
