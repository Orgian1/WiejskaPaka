# Zgodność projektu regulaminu z funkcjami demo — 18.10.2026

Porównanie techniczne dokumentu `REGULAMIN_KUPUJACYCH_PROJEKT_PL.md`
z kodem aplikacji. To lista różnic do wdrożenia i odbioru, nie opinia prawna.
Projekt regulaminu pozostaje roboczy i nie został opublikowany w interfejsie.

| Zapis projektu | Obecna funkcja | Brak do zamknięcia |
| --- | --- | --- |
| § 1: dane operatora i status sprzedawcy | Konto rolnika, profil gospodarstwa, wewnętrzny testowy przegląd profilu | Dane rzeczywistego operatora; model statusów sprzedawcy i ich prezentacja przed zakupem; zatwierdzona weryfikacja |
| § 2: opis i oznaczenie produktu | Nazwa, cena, dostawa, stan magazynowy; zachowany zapis warunków zakupu | Formularz i walidacja wymaganych informacji o konkretnych rodzajach żywności; proces przeglądu i moderacji ofert |
| § 3: cena, jedna dostawa na przesyłkę | Koszyk, podgląd kwoty, grupowanie przesyłek, dokładne grosze | Rzeczywisty operator płatności i uzgodnione przepływy środków; obecnie wyłącznie symulacja |
| § 4: sprawdzenie towaru i PIN | Potwierdzenie sprawdzenia towaru oraz odbioru całej przesyłki; ograniczone odzyskiwanie istniejącego PIN-u | Dedykowany proces odmowy przyjęcia i rozstrzygania przyczyn; obsługa częściowego odbioru nie jest gotową funkcją demo |
| § 5: niewykonana dostawa | Testowy pełny zwrot i historia zdarzeń | Rzeczywisty zwrot przez operatora, obsługa wyjątków i uzgodnione zasady odpowiedzialności |
| § 6: reklamacja przez panel | Informacja o prawach kupującego, zapis zakupu i historia | Brak panelu reklamacji: przyjęcia zgłoszenia, potwierdzenia, kierowania do sprzedawcy, statusów i obsługi terminów |
| § 7: e-mail i panel | Powiadomienia w panelu, kontrakt dozwolonych kanałów, lokalna skrzynka resetu hasła | Weryfikacja adresu i rzeczywista wysyłka poczty, kolejka z ponowieniami i potwierdzonym dostarczeniem; sama polityka kanałów nie wysyła wiadomości |
| § 8: prywatność, zgłoszenia i moderacja | Dostęp do danych według ról, cofanie sesji, izolowane kopie i testowy przegląd profilu | Docelowa polityka prywatności, mechanizm zgłoszeń treści, moderacja i odwołania; kolejka profili nie jest mechanizmem reklamacyjnym |

## Ważne rozróżnienia przy odbiorze

- Anulowanie nieopłaconego zakupu, testowy zwrot po opłaceniu i reklamacja
  produktu to różne procesy. Nie wolno oznaczyć reklamacji jako wdrożonej
  tylko dlatego, że istnieje przycisk anulowania lub zdarzenie zwrotu.
- Przesyłka wieloproduktowa jest obecnie odbierana w całości. Projektowy
  zapis o odmowie części towaru wymaga osobnego projektu operacji, magazynu
  i rozliczenia, zanim stanie się obietnicą działającej usługi.
- Przegląd profilu administratora nie potwierdza tożsamości, statusu
  przedsiębiorcy ani spełnienia wymagań dotyczących żywności.
- Przyjęcie zasad demo nie oznacza przyjęcia przyszłego regulaminu sprzedaży.
- Nie należy dodawać pola „akceptuję regulamin” powiązanego z dokumentem,
  który nadal zawiera puste dane operatora i opis niegotowych funkcji.

## Kolejność dalszej implementacji

1. Ustalić model sprzedawcy i umów oraz dane operatora.
2. Zaprojektować zgłoszenia problemów i reklamacje z dostępem wyłącznie
   stron zakupu oraz upoważnionego administratora.
3. Określić odmowę całej przesyłki i części produktów wraz z wpływem na
   magazyn, jedną opłatę dostawy, historię oraz idempotencję zwrotów.
4. Dopracować informacje o produktach i bezpieczną komunikację e-mail.
5. Dopiero po zgodności funkcji i zatwierdzeniu dokumentów podłączyć je
   do właściwych miejsc interfejsu i potwierdzać wersję przyjętych warunków.

Podstawa sprawdzenia: `web/index.html`, `web/app.js`, `web/dashboard.js`,
`backend/app.py`, `backend/notification_policy.py`, `backend/password_reset.py`
oraz wymieniony projekt regulaminu. Brakujące funkcje nie są zastępowane
planami wydajności ani wynikami regresji istniejącego zakresu.
