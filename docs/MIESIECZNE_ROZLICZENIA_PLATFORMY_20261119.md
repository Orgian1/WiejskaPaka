# Miesięczne rozliczenia opłat WiejskaPaka — zasady wdrożenia

Status: przygotowanie księgowe, bez automatycznego wystawiania faktur.

## Zakres
- Każda należna opłata platformy ma własny identyfikator źródła i daty: operacji, otrzymania zapłaty oraz wykonania usługi (mogą się różnić).
- Raport grupuje opłaty za punkty odbioru, prowizje za wypłaty sprzedawców oraz reklamy **oddzielnie dla każdego sprzedawcy i rodzaju usługi**.
- Rozliczenia pozostają w całkowitych groszach. Korekty i zwroty są zapisywane jako osobne, podpisane pozycje; nie nadpisujemy historii.
- Nie wolno ujmować całej wartości sprzedaży rolników, doładowań portfela ani kosztów dostaw jako przychodu platformy.
- Miesięczny raport nie jest fakturą ani dokumentem KSeF.

## Warunki przed uruchomieniem fakturowania
1. Ustalić status podatkowy WiejskaPaka, VAT, status i dane nabywców, właściwy podmiot wystawiający fakturę.
2. Zweryfikować terminy fakturowania, w tym skutki pobierania opłat z góry i daty obowiązku podatkowego. Nie zakładać, że wszystkie faktury można wystawić dopiero na koniec miesiąca.
3. Ustalić, które operacje mogą być ujęte na fakturze zbiorczej, które wymagają odrębnego dokumentu i jak dokumentować korekty.
4. Wybrać dostawcę API faktur/KSeF; sprawdzić tryb testowy, autoryzację, identyfikatory faktur, obsługę błędów, duplikatów i korekt.
5. Połączyć eksport z faktycznym, niezmiennym rejestrem transakcji. Przed wysłaniem faktury wykonać uzgodnienie sum z rejestrem finansowym i płatnościami operatora.
6. Rozdzielić środowisko testowe od produkcyjnego. Bez zatwierdzenia konfiguracji nie wysyłać dokumentów do KSeF ani e-maili do klientów.

## Gotowe elementy
- `backend/monthly_platform_fees.py`: grupowanie i eksport CSV w groszach z przekazanych wpisów.
- `tests/test_monthly_platform_fees.py`: testy sumowania, korekt i eksportu.

## Czego jeszcze nie ma
- Połączenia z rzeczywistymi zapisami portfela i opłatami za punkty.
- Weryfikacji statusu podatkowego i wymagalności dokumentu dla konkretnej operacji.
- Integracji z API programu fakturowania i KSeF.
- Automatycznej wysyłki faktur.
