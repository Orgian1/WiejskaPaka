# Miesięczny panel finansowy administratora — 18.10.2026

Administrator wybiera miesiąc i otwiera „Pokaż raport finansowy (test)”.
Widok pokazuje kwoty w złotych: produkty, dostawę, sumę, prowizję i należności
sprzedawców. Liczniki dotyczą pozycji produktów, nie całych przesyłek.
Kwoty pochodzą z istniejącego raportu API; interfejs nie oblicza na nowo
podziału pieniędzy. Sprawdza nieujemne bezpieczne liczby całkowite, miesiąc,
rodzaj raportu oraz zgodność sum. Formatowanie BigInt zachowuje grosze.

Przycisk „Pobierz raport CSV (TEST)” korzysta z istniejącej ścieżki API
wymagającej uprawnień administratora. Token jest przekazywany w nagłówku,
bez umieszczania go w URL lub pamięci trwałej przeglądarki. Odpowiedź musi
mieć poprawny status i typ CSV. Nazwa pliku zawiera zweryfikowany miesiąc.
Tymczasowy adres pliku jest zwalniany po pobraniu. Zmiana konta, miesiąca,
odświeżenie panelu lub usunięcie raportu unieważnia oczekujące pobranie.

Zmiana miesiąca usuwa stary raport i unieważnia wcześniejsze żądania.
CSV przedstawia aktualny stan w chwili pobrania; zwroty i zmiana stanu
płatności mogą zmienić kwoty względem wcześniejszego widoku. Nie jest to
dokument księgowy ani potwierdzenie rzeczywistej płatności. Plik już pobrany
przez użytkownika pozostaje na jego komputerze po wylogowaniu.

## Sprawdzenie

Nowe scenariusze JavaScript uruchamiane przez Python obejmują czytelność kwot,
maksymalne dokładne grosze, wadliwe wartości i sumy, niewłaściwy miesiąc,
autoryzowane pobranie, błędy HTTP i typu odpowiedzi oraz zmianę widoku lub
konta podczas oczekiwania na odpowiedź i zawartość pliku.

Istniejące testy rzeczywistego Chromium rozszerzono o pobranie CSV przy
320 i 1280 px, odczyt jego zawartości, usunięcie raportu po zmianie miesiąca
i dodatnie kwoty po pełnym odbiorze oraz przekazaniu jednej pozycji do
symulowanego rozliczenia. Wynik lokalnie pominiętego testu Chromium nie jest
wynikiem natywnej przeglądarki. Wyniki pełnej regresji i CI zostaną zapisane
po zakończeniu kontroli dla konkretnego commitu.

Nie zmieniono schematu bazy, zasad płatności, rozliczeń ani zwrotów.
Nie uruchomiono integracji produkcyjnych. Zmiany dotyczą gałęzi
`wiejskapaka-import`.
