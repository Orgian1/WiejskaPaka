# Granice tego wydania i dalsze prace

## Bramy wymagające innego środowiska

1. Uruchomić `docker-compose.postgres.yml`, zaliczyć natywne testy API,
   współbieżności, wszystkich migracji i rolę bez uprawnień administratora.
   Obecna sesja nie uzyskała działającego serwera PostgreSQL.
2. Uruchomić Chromium z rzeczywistym HTTP na telefonicznych i desktopowych
   rozmiarach ekranu. Sprawdzić rejestrację, koszyk wielu rolników, PIN,
   przełączanie kont, komunikaty o błędach i dostępność. Obecne testy struktury
   HTML i JavaScript nie są testem działającej przeglądarki.
3. Zgodnie z najnowszym poleceniem kontynuujemy bez GitHub. Pełne ZIP i lokalna
   historia Git są podstawowym sposobem przekazania kodu; połączenie zdalne
   nie jest warunkiem dalszej pracy.

## Funkcjonalności niewykazane jako ukończone

- Dodano backend i interfejs wyszukiwania aktywnych punktów i produktów dla
  100 m / 500 m / 1 km / 5 km, polskie nazwy, filtry cen, geometrię i zarządzanie
  punktami. SQLite, HTTP oraz zachowanie JavaScript są sprawdzone. Natywny
  PostgreSQL, prawdziwy GPS telefonu i Chromium pozostają do weryfikacji.
  Pomiar jest sferyczny w linii prostej, a nie trasą drogową. Nie ma zewnętrznych
  map ani automatycznego geokodowania. Szczegóły: `docs/WYSZUKIWANIE_LOKALNE.md`.
- Weryfikacja sprzedawcy jest szkieletem testowym: nie ma bezpiecznej,
  końcowo zweryfikowanej procedury zbierania NIP/PESEL, daty urodzenia i konta
  po 20 rzeczywistych transakcjach. Nie należy wysyłać tych danych do demo.
- Nie wykazano kompletnego pobierania opłaty za dodanie punktu ani rocznego
  rozliczenia zawierającego wszystkie takie koszty.
- Funkcja matematyczna 75/20/5 istnieje i jest testowana. To nie jest dowód
  wdrożenia prawidłowej procedury dla nieodebranego towaru, terminów odbioru
  ani zgodności automatycznych potrąceń z prawami konsumenta.
- Interfejsy `frontend-prototyp/` i `web/` są różnymi warstwami demonstracyjnymi.
  Nie uznajemy wszystkich funkcji prototypu za zintegrowane z backendem.
- Dodano i sprawdzono na SQLite automatyczne wygaszanie nowych nieopłaconych
  rezerwacji po 30 minutach oraz limit 10 zakupów na konto. Starsze zamówienia
  nie są wygaszane wstecz. Częściowo opłacone przesyłki wymagają jawnego
  anulowania ze zwrotem; ochrona przed masowym zakładaniem kont i natywna
  weryfikacja PostgreSQL pozostają do wykonania. Szczegóły:
  `docs/REZERWACJE_MAGAZYNU.md`.
- Odpowiedzi idempotencji są teraz szyfrowane osobnym kluczem, z ograniczeniem
  ujawniania PIN-u do 24 godzin i automatyczną retencją. Nadal wymagane są
  niezależny magazyn kluczy, plan backupów/wycofywania kluczy i bezpieczny
  docelowy proces przekazywania lub odzyskiwania PIN-u. Szyfrowanie nie zastępuje
  tych prac. Szczegóły: `docs/SZYFROWANIE_ODPOWIEDZI_ZAKUPU.md`.
- Nowe zakupy mają osobny zapis pierwotnej nazwy, ceny i danych punktu,
  chroniony przed zwykłą aktualizacją/usunięciem w bazie. Starszych zakupów
  nie uzupełniamy z bieżącego katalogu. Pozostają: natywna weryfikacja PostgreSQL,
  polityka retencji i kontrolowane usuwanie/anonimizacja, niezależny audyt.
  Zapis testowy nie jest fakturą ani dowodem płatności. Szczegóły:
  `docs/HISTORIA_ZAKUPOW.md`.
- Nie ma zakończonego, niezależnego przeglądu wszystkich reguł dostępu/RLS,
  ochrony danych, odzyskiwania kont, retencji danych, regulaminu i procedur
  reklamacyjnych. Komunikat o prawach konsumenta nie zastępuje tych prac.

Nie potwierdzamy wcześniejszego szacunku 90% ukończenia ani wszystkich
360 numerowanych pozycji paczki. Do rzetelnego procentu potrzebna jest
skończona i zatwierdzona lista wymagań wraz z dowodami akceptacji.

## Świadomie odłożone na później

Rzeczywisty operator płatności, bankowe wypłaty, domena, hosting i Neon
pozostały niepodłączone zgodnie z poleceniem. Nie są częścią zaliczonych testów.
Nie włączać ich automatycznie po pobraniu tego archiwum.
