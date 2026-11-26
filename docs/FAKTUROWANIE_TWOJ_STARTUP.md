# Fakturowanie w Twój StartUp

W panelu administratora otwórz **Fakturowanie – Twój StartUp**. Tryb symulacji ma osobny rejestr i licznik. Dane wpisane w tym trybie są przeznaczone do prób z fikcyjnymi nabywcami.

1. Po uzgodnieniu wpływu na subkonto zapisz identyfikatory transakcji i rozliczenia operatora, datę transakcji, datę wpływu oraz dane nabywcy. Wpisz wyłącznie kwotę należną WiejskiejPace.
2. Otwórz listę **Do wystawienia** i skopiuj dane odpowiedniej pozycji. Wystaw dokument ręcznie w CRM według zasad fundacji.
3. Wróć do panelu i wpisz numer oraz faktyczną datę wystawienia. Po zapisaniu dokument pojawia się w zakładce **Wystawione**. Rejestr blokuje ponowny zapis tej samej transakcji i ponowne użycie numeru faktury w tym samym trybie.
4. Zapisz zwrot z odrębnym numerem zdarzenia i potwierdzeniem rozliczenia. Zwrot przed fakturą pomniejsza kwotę do wystawienia. Pełny zwrot zamyka pozycję. Zwrot po wystawieniu tworzy pozycję korekty ze wskazaniem oryginału. Kwota oryginalnego dokumentu jest zachowana.
5. Wybierz miesiąc, aby zobaczyć wpływy po zwrotach i prowizje. Licznik faktur korzysta z dat wystawienia zapisanych dokumentów. Na 100 dokumentów miesięcznie pozostaje bezpłatny limit, a każdy rozpoczęty blok dodatkowych 100 kosztuje 40 zł. Licznik obejmuje dokumenty zarejestrowane w WiejskiejPace. Pozostałe dokumenty beneficjenta należy uwzględnić przy uzgadnianiu limitu w CRM.

Przy potwierdzonym rozliczeniu prowizji wpisuje się wartość całej wypłaty sprzedawcy jako podstawę kontroli. Kwota do faktury wynosi wyłącznie 5% i jest zaokrąglana do pełnego grosza metodą half-up. W symulacji kwotę i właściciela porównuje się ze stanem zakończonej wypłaty. Miesięczne zestawienie sprzedawców grupuje wpisy powiązane z ich kontami według usługi. Służy do uzgodnienia danych przed wystawieniem dokumentów.

| Przepływ | Ujęcie w rejestrze Twój StartUp |
| --- | --- |
| Zasilenie portfela klienta lub sprzedawcy | Saldo użytkownika poza rejestrem wpływów platformy |
| Rozliczenie produktów i dostawy | Należność uczestników poza rejestrem wpływów platformy |
| Wypłata klienta | Rozliczenie salda bez prowizji WiejskiejPaki |
| Rozliczona wypłata sprzedawcy | Prowizja 5% jako wpływ platformy. Pozostała kwota należy do sprzedawcy |
| Opłacony punkt odbioru lub reklama | Kwota rozliczonej usługi jako wpływ platformy |
| Bezpłatny punkt, anulowanie lub nieudana wypłata bez wpływu | Brak pozycji do faktury |

Rejestr nie zmienia sald portfeli, nie aktywuje zakupionych usług i nie wysyła danych do CRM ani do KSeF. Dotychczasowe symulatory zamówień i zestawienia testowe pozostają odrębnymi ścieżkami demonstracyjnymi. Do księgowania prowizji używa się wyłącznie rozliczonej wypłaty z portfela, aby uniknąć naliczenia prowizji drugi raz na podstawie raportu testowych zamówień.

## Uruchomienie modułu i dalsze decyzje

- SQLite udostępnia zakładkę w trybie symulacji. Na PostgreSQL stosuje się migrację `database/upgrade_incubator_invoicing.sql` i włącza `WP_ENABLE_INCUBATOR_INVOICING=1`. Na istniejącej bazie z RLS migracja uzupełnia polityki bez przyznawania klientowi SQL bezpośredniego dostępu do danych fakturowych.
- Tryb ręcznego zapisu potwierdzonych wpływów wymaga PostgreSQL z bramką RLS i osobnej flagi `WP_ENABLE_INCUBATOR_MANUAL_SETTLEMENTS=1`. Włącz ją po uzgodnieniu zasad z fundacją i PayU, po kopii bazy oraz próbie migracji na środowisku testowym. Na wdrożonej domenie brak tej konfiguracji pozostawia moduł wyłączony.
- PayU musi zatwierdzić przepływ portfeli, rolę sprzedawców, miejsce pobrania 5%, rozdział środków i identyfikatory uzgodnień. Integracja musi kierować na subkonto fundacji tylko środki należne platformie. Testy na rachunkach i mechanizmach sandbox operatora pozostają do wykonania po uzyskaniu konfiguracji. [Dokumentacja PayU Marketplace](https://developers.payu.com/europe/pl/docs/services/marketplace/)
- Z fundacją i księgowością ustal dane wymagane na dokumentach, traktowanie dat transakcji i wpływu, stawki VAT, sposób korekt i ewentualne faktury zbiorcze. Rejestr nie oblicza VAT i nie aktywuje zbiorczego wystawiania faktur.
