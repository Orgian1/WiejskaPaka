# Paczka #59 — raport końcowy

Repozytorium: `Orgian1/WiejskaPaka`. Nowa gałąź:
`codex/issue-59-pre-vps-20261113`, utworzona z aktualnej
`codex/product-categories-filters-20261113` przy
`6af63fa5efc8d19be8f5c53695bb6195bb8b9139`.
Commit kodu poddany regresji: `96fd8868dab23ef22e87f3d3c51f72ca7f787612`.
Commit `0832f3a` dostosowuje jeden test statyczny ochrony przed spóźnioną
odpowiedzią; kod aplikacji pozostaje identyczny z `96fd886`. Końcowy commit
zawiera wyłącznie dokumentację i dowody testów.

## Wykonane zmiany

- Logowanie i odzyskiwanie hasła znikają po zalogowaniu, także gdy opóźniona
  odpowiedź opcji resetu wraca już po zmianie sesji. Zmiana hasła pozostaje
  w ustawieniach. Sekrety resetu i szkice nie przechodzą między kontami.
- Klient nie ma kontrolek wysyłania zdjęć; zdjęcia produktów i panel sprzedawcy
  pozostają dostępne.
- Czerwone liczniki pokazują unikalne ulubione, pozycje koszyka i aktualne
  zamówienia sprzedawcy. Zero jest ukryte. Prywatny endpoint podsumowania
  sprawdza bieżącą sesję i role, ogranicza zapytania do właściciela danych;
  odpowiedzi ze starej sesji są ignorowane. Synchronizacja następuje po operacji,
  powrocie do okna oraz co 30 sekund w widocznym panelu.
- Jeden zwinięty formularz „Zgłoś problem / Kontakt” znajduje się na dole,
  wspólny dla klienta i sprzedawcy. Zachowano zapis zgłoszeń zakupowych,
  odpowiedzi i obsługę administratora. Zmiana konta usuwa prywatny szkic.
- „Blisko mnie” korzysta z wybranego/zapisanego miejsca, a bez niego z GPS
  po kliknięciu. Ma osobne komunikaty dla odmowy, niedostępności, timeoutu,
  braku API i niezabezpieczonego kontekstu. Wybór ręczny pozostaje dostępny.
- Zamówienia sprzedawcy są pogrupowane w domyślnie zamknięte punkty odbioru;
  dostawy na adres mają oddzielną sekcję. Wiersze powstają dopiero po rozwinięciu,
  po 20 na stronę, z zachowaniem działań i PIN-ów. Dodatkowy panel przesyłek
  i zamówień także wyświetla partie po 20. Liczniki wykluczają historię.
- Nie zmieniono reguł kwot, prowizji, płatności i stanów zamówień.
  Nie dodano migracji SQL; istniejący manifest 45 plików ma zgodne sumy.

## Photon — diagnoza i granice potwierdzenia

Poprzedni adapter wymuszał `lang=pl`. Photon odrzuca język nieobecny w indeksie,
choć zapytanie bez parametru języka może działać. Potwierdza to
[kod upstream RequestFactoryBase, linie 75–83](https://github.com/komoot/photon/blob/01dff5a5475c96d7a0493dfd12f06f55c8ff7136/src/main/java/de/komoot/photon/query/RequestFactoryBase.java#L75).
Adapter używa teraz `lang=default`, obsługiwanego przez kontrakt usługi,
i nadal ogranicza kraj do Polski. Test kontrolowanego dostawcy odtwarza
odrzucenie poprzednich parametrów i powodzenie poprawionego endpointu.

Dodatkowo opcjonalne pola odpowiedzi, np. ulica/numer/kod, mogą być null przy
wynikach miejscowości; wcześniej powodowały odrzucenie poprawnego wyniku.
Normalizacja toleruje ich brak, zachowując walidację współrzędnych i rozmiaru.
HTTPX korzysta z systemowego magazynu zaufania TLS; launcher zachowuje
obsługiwane ustawienia proxy i certyfikatów, również ich małe litery.
Weryfikacja TLS pozostaje włączona. Błąd konfiguracji certyfikatów jest
bezpiecznie raportowany jako niedostępność, bez ujawnienia lokalnych ścieżek.

Można wyszukiwać miasto, ulicę lub kod pocztowy, również bez pola miasta.
Testy obejmują Wroclaw, Wrocław, Łódź, polskie znaki, ulicę z numerem,
kod pocztowy, błędne dane i odpowiedzi usługi. Frontend ma timeout i ignoruje
spóźnione wyniki; użytkownik jawnie wybiera wynik.

**Nie ustalono zdalnie jednej pewnej przyczyny konkretnego incydentu Windows.**
Samo zgłoszone HTTP 200 z minimalnego zapytania nie zawiera informacji o tym,
czy zawiodły parametry, pola odpowiedzi, czy magazyn certyfikatów aplikacji.
Cztery próby publicznego Photon z tej chmury zostały zablokowane przez
proxy/politykę sieciową, także minimalne urllib oraz poprawiony adapter.
Raport diagnostyczny ma `EXTERNAL_ACCESS_NOT_CONFIRMED`. Nie jest to
potwierdzenie działania publicznej usługi ani test na Windows.
Skrypt `python -m scripts.check_photon_demo` umożliwia bezpieczne porównanie
na komputerze, na którym wystąpił problem; nie zapisuje sekretów ani wynikowych
adresów. Szczegóły zawiera instrukcja odbioru.

## Testy

Wyniki końcowe i sumy źródeł znajdują się w `audits/issue59_20261113/`.
| Zestaw | PASS | FAIL | SKIP |
| --- | ---: | ---: | ---: |
| Pełna izolowana regresja SQLite, 408 modułów | 4979 | 0 | 109 |
| Natywny PostgreSQL 17, jednorazowe bazy | 106 | 0 | 0 |
| Rozszerzony Chromium, 26 modułów | 136 | 0 | 0 |
| Zdjęcia, osobny zestaw przeglądarkowy | 2 | 0 | 0 |

Kontrola aplikacji przez HTTP w szerokościach **320, 360, 390, 768 i 1280 px**:
PASS. Nie jest doliczana jako dodatkowe przypadki pytest. Zestawy nakładają się,
więc ich sum nie należy przedstawiać jako liczby unikalnych testów.

109 SKIP w izolowanej regresji: 106 przypadków wymagających PostgreSQL
(uruchomionych osobno: 106 PASS), jeden rozszerzony test ról przeglądarkowych
(uruchomiony w bramce Chromium) i dwa przypadki odmowy na systemach non-POSIX,
nieodpowiednie dla tego Linuxa. Nie wyłączano testów w celu uzyskania PASS.

Pierwszy przebieg wykrył jeden nieaktualny test statyczny oczekujący `clear`
bezpośrednio po sprawdzeniu sesji. Dodana aktualizacja licznika mieści się
pomiędzy tymi operacjami. Test teraz wymaga ochrony zarówno licznika, jak i
czyszczenia/renderowania listy. Ponowiono zmieniony moduł w części 4/4,
z zachowaniem wyników niezmienionych modułów i weryfikacją sum plików.

Bramki natywne wykonano na niezmienionym kodzie `96fd886`, przed dostosowaniem
tego jednego testu statycznego spoza ich zestawów. Sumy **wszystkich testów
obu bramek**, aplikacji, zależności i workflow odpowiadają końcowym źródłom;
`summary.json` zawiera jawną kontrolę tych sum. Globalne sumy całego katalogu
testów w pierwotnych raportach natywnych pochodzą sprzed tej korekty.
Termin bramki rozszerzonej zwiększono lokalnym wrapperem do 1200 sekund,
bez zmiany zestawu, asercji ani testów; standardowy limit był zbyt krótki dla
rozszerzonego zestawu przy równoległej regresji. Pliki raportów nie zawierają
przechwyconych logów ani sekretów.

Nowe testy przeglądarkowe obejmują szerokości 320/1280 px, warianty GPS,
odtwarzanie liczników, zmianę kont i listę 435 kontrolowanych zamówień
(335 aktualnych i 100 historycznych). To test skalowania interfejsu z danymi
kontrolowanymi; nie jest tworzeniem 435 rzeczywistych operacji finansowych.

## Ograniczenia i przekazanie

- Publiczny Photon i dokładna przyczyna incydentu na Windows wymagają
  diagnostyki w docelowej sieci. Ręczny wybór miejsca i GPS nie zależą od Photon.
- Testy telefonu i tabletu w tej paczce to przeglądarka Chromium z kontrolowanym
  GPS oraz zadanymi rozmiarami. Fizyczny telefon, systemowe zgody, Windows,
  rzeczywiste e-maile i testy na docelowym HTTPS pozostają do odbioru właściciela.
- Ogólny formularz kontaktowy nadal wymaga konfiguracji usługi pocztowej;
  bez niej wysyłanie jest jawnie wyłączone. Zgłoszenia zakupowe zapisują się
  w bazie niezależnie od SMTP. Produkcyjnej poczty nie włączano.
- GitHub API jest w tej chmurze blokowane odpowiedzią CONNECT 403.
  Zapis Git HTTPS działa; stan rzeczywistej próby utworzenia PR opisano poniżej.

[Uruchomienie demo, lista odbiorowa i bezpieczna aktualizacja VPS](ISSUE_59_ODBIOR_I_VPS_2026-11-13.md).
Nie wdrażano na VPS, nie zmieniano main, danych produkcyjnych ani prawdziwych
płatności. Używano wyłącznie lokalnych baz i fikcyjnych kont testowych.

## GitHub i Pull Request

Nowa gałąź została utworzona na origin przez `git push --set-upstream`.
Próba `gh pr create` z bazą kategorii, nową gałęzią, konkretnym tytułem i treścią
z pliku zakończyła się `Post https://api.github.com/graphql: Forbidden`.
**Pull Request nie został utworzony.** Istniejąca obsługa uwierzytelnienia Git
pozwala zapisywać commity, ale nie znosi blokady API. Nie obchodzono proxy.

Gotowa treść: [PR_ISSUE_59.md](PR_ISSUE_59.md).
[Ręczne utworzenie PR z właściwą bazą](https://github.com/Orgian1/WiejskaPaka/compare/codex/product-categories-filters-20261113...codex/issue-59-pre-vps-20261113?expand=1).
Automatyczne utworzenie wymaga dostępnego GitHub API i uprawnień do PR;
wartości tokenów nie należy przesyłać w rozmowie. Środowiska nie publikowano.
