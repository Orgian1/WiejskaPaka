# WiejskaPaka — PayU: bezpieczne uruchomienie testowe

Stan: przygotowanie techniczne, bez połączenia z prawdziwym PayU.

## Obecne zabezpieczenia
- Produkcja PayU jest wyłączona i blokowana konfiguracją.
- Domyślny adapter płatności i wypłat odmawia transakcji.
- Symulator działa wyłącznie w pamięci testów; nie zasila portfela.
- Identyfikatory operacji i zwrotów są idempotentne, a łączna wartość zwrotów nie może przekroczyć płatności.
- Wypłata sprzedawcy: 5% prowizji liczone w groszach; wypłata klienta: bez prowizji WiejskaPaka.
- Schemat dziennika płatności, zdarzeń, zwrotów i wypłat jest **wyłącznie testowy**. Nie został podłączony do produkcyjnej bazy danych.
- Dziennik ma unikatowe identyfikatory zdarzeń i odwołanie do księgowania portfela; nie jest jeszcze kompletnym mechanizmem rozliczeniowym.
- Przejścia stanów i porównanie kwot są sprawdzane testami, ale nie stanowią weryfikacji autentyczności webhooka.

## Przed podłączeniem PayU
1. Ustalić z PayU umowę marketplace, przepływ środków, KYC/KYB, obsługę portfeli i wypłat; nie zakładać, że zwykłe API płatności obsługuje przelewy do użytkowników.
2. Uzyskać dane środowiska PayU SANDBOX. Przekazać je przez sekrety serwera/CI, **nigdy w repozytorium ani na czacie**.
3. Zaimplementować i zweryfikować rzeczywisty adapter PayU: OAuth, utworzenie zamówienia, statusy, podpis/wiarygodność powiadomień, powtórzenia i opóźnienia.
4. Podłączyć atomowy, idempotentny zapis do istniejącego portfela i jego księgi, po audycie rzeczywistego schematu danych oraz zabezpieczeń RLS.
5. Zweryfikować w PayU SANDBOX realne transakcje, zwroty, rozbieżności i rozliczenia; dopiero potem rozważyć włączenie produkcji z osobną zgodą.

Nie należy traktować obecnych testów jednostkowych jako potwierdzenia gotowości prawdziwych płatności.
