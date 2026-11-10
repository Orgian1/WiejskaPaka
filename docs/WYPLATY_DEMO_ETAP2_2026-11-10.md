# WiejskaPaka — zamykanie wniosków wypłaty w demo

Kontynuacja pakietu z PR #51. Tylko prywatne środowisko testowe/development
z WP_ENABLE_WALLET_PREVIEW=1. Żadna z poniższych operacji nie łączy się z bankiem
ani operatorem płatności. API zwraca transfer_executed=false.

## Działanie

Wniosek zapisuje niezmienne warunki w groszach: kwotę brutto, rolę właściciela,
stawkę prowizji, prowizję i kwotę netto. Sprzedawca: 5%, klient: 0%.
Zaokrąglenie half-up. Kwota rezerwowana obejmuje prowizję, więc nie ma drugiego
obciążenia. Zmiana roli lub przyszłej taryfy nie przelicza już zapisanych wniosków.

Właściciel może anulować własny oczekujący wniosek przyciskiem w historii
portfela. Cała kwota rezerwacji wraca do dostępnego salda, bez prowizji.
Administrator ma oddzielny widok oczekujących wniosków i przycisk
„Zakończ symulację wypłaty (TEST)”. Zakończenie usuwa kwotę brutto z rezerwy;
nie zwiększa dostępnego salda. Zapisane netto i prowizja pozostają warunkami
zakończonej symulacji, bez rzeczywistego przelewu.

Przykład: 100 zł salda sprzedawcy, wniosek 40 zł, prowizja 2 zł, netto 38 zł.
Po wniosku: 60 zł dostępne + 40 zł rezerwy. Po anulowaniu: 100 zł + 0 zł.
Po zakończeniu przez admina: 60 zł + 0 zł; zapis symulacji obejmuje 38 zł netto
oraz 2 zł prowizji. Tylko jeden z dwóch stanów końcowych może wygrać.

Każda decyzja jest osobnym, niezmiennym zdarzeniem dziennika z rewizją,
autorem i końcowym saldem. Wspólna blokada konta chroni równoległe anulowanie,
zakończenie, nowe wypłaty i doładowania. Ponowienie identycznej decyzji zwraca
poprzedni wynik; przeciwna decyzja po rozstrzygnięciu daje 409. Ponowienie
pierwotnego wniosku zwraca jego aktualny stan oraz pierwotnie zapisane warunki.
Kontrola integralności obejmuje stary dziennik i nowe zdarzenia wraz z zapisami
salda. Widok portfela odczytuje saldo, historię i warunki jednym zapytaniem.

## Uruchomienie i kontrola

```bash
python scripts/run_phone_demo.py --full-demo
```

1. Zaloguj klienta lub sprzedawcę, doładuj 100 zł, ustaw PIN i złóż wypłatę 40 zł.
2. Anuluj wniosek w historii; po odświeżeniu nadal ma być 100 zł dostępne.
3. Złóż drugi wniosek 40 zł, wyloguj się i zaloguj na wygenerowane konto admina.
4. W zakładce „Wypłaty” sprawdź kwoty i zakończ symulację. Wniosek znika
   z oczekujących. Ponowne kliknięcie/ponowienie nie może drugi raz rozliczyć rezerwy.
5. Wróć na konto właściciela. Saldo: 60 zł dostępne, 0 zł rezerwy. Historia
   pokazuje stan końcowy i informację o braku przelewu. Sprawdź telefon i komputer.

Portfel nadal pozostaje oddzielony od płatności zamówień, przychodów sprzedawcy
oraz zwrotów zamówień. Nie wolno traktować obu symulatorów jako jednego salda.
Ten pakiet domyka wnioski portfela, nie integrację operatora ani księgowość live.

## Migracja i uprawnienia

Nowa migracja: database/optional_wallet_withdrawals.sql, po
optional_wallet_preview.sql. Dodaje wallet_preview_terms i
wallet_preview_resolutions, bez zmiany dotychczasowych tabel i kwot.
Istniejące oczekujące wnioski otrzymują zapis warunków według dotychczasowej
stałej polityki 5%/0% podczas migracji. Nie ma automatycznej migracji PostgreSQL;
brak nowych tabel blokuje preflight i start modułu.

Na SQLite instalator dodaje tabele i zapisuje warunki tylko dla wniosków,
które jeszcze ich nie mają. Istniejące warunki nie są nadpisywane. Triggery
blokują aktualizację i usunięcie warunków i decyzji. PostgreSQL wymaga uprawnień
SELECT,INSERT na nowych tabelach, bez UPDATE i DELETE. Szablon nowej testowej
bazy oraz natywny fixture nadają te ograniczenia po ogólnych grantach.

Przed wdrożeniem: kopia bazy i kluczy, próba odtworzenia, zatrzymanie zapisów,
przejrzenie migracji, wykonanie na odtworzonej kopii, manifest i preflight.
Nie zmieniono VPS. Procedura ogólna: WDROZENIE_I_WYCOFANIE_DEMO_2026-11-10.md.

Wycofanie do starego kodu po zapisaniu nowych zdarzeń wymaga wyłączenia
WP_ENABLE_WALLET_PREVIEW=0: stary audyt nie rozumie nowych rewizji.
Nie usuwać nowych tabel i nie przywracać starego salda automatycznie.
Zachować cały dziennik; przywracanie danych przeprowadzać wyłącznie według
sprawdzonej procedury, po zabezpieczeniu stanu po awarii.

## Weryfikacja

Wyniki zostaną zapisane po zakończeniu testów dla tego pakietu.
