# Ograniczony proces obsługi kolejki — etap testowy

`backend.reset_mail_worker.run_process` uruchamia pojedynczy proces potomny
przez metodę spawn. Wywołujący jawnie przekazuje funkcję połączenia z bazą,
pęk kluczy oraz transport. Wszystkie przekazywane obiekty muszą nadawać się
do serializacji spawn. Nie ma domyślnego połączenia, odczytu środowiska,
transportu SMTP, pętli demona ani automatycznego uruchamiania przez API.

## Limity i zatrzymanie

Jedno wywołanie obsługuje maksymalnie 1–25 prób pobrania zadania (domyślnie
10) i działa przez 1–60 sekund (domyślnie 30). Pusta kolejka kończy proces
od razu. Błędne limity są odrzucane przed utworzeniem procesu. Każda próba
korzysta z własnego połączenia zamykanego przez `dispatch_once`.

Po upływie limitu rodzic ustawia sygnał zatrzymania. Po sekundzie okresu
ochronnego kończy proces, jeżeli ten nadal działa; w razie potrzeby używa
kill. Sprzątanie może dodać do pięciu sekund do nominalnego limitu. Sygnał
jest sprawdzany przed następnym pobraniem, więc zakończona próba nie daje
zgody na rozpoczęcie kolejnej po odebraniu sygnału.

Wynik zawiera wyłącznie stały status i liczniki ze zbioru dopuszczonych kodów.
Wyjście standardowe i diagnostyczne kodu transportu w procesie potomnym
jest tłumione. Błąd konfiguracji procesu lub połączenia daje WORKER_FAILED,
bez wyjątku, ścieżki, odbiorcy, tokenu i danych dostępowych.

## Brak automatycznego ponowienia niepewnej próby

TIME_LIMIT i WORKER_FAILED zwracają `counts: null`: proces mógł rozpocząć
transport, więc nie można wnioskować o braku wysyłki z braku wyniku.
Ponowne uruchomienie musi korzystać z trwałego rejestru kolejki.
Przerwanie przed znacznikiem rozpoczęcia pozwala odzyskać wygasłą dzierżawę.
Przerwanie po znaczniku prowadzi do uncertain, bez automatycznego ponowienia.
ACCEPTED oznacza kod zwrócony przez przekazany transport; nie potwierdza
doręczenia do skrzynki. Testy używają sztucznego transportu w pamięci.

## Granice odbioru

To ograniczenie czasu i liczby zadań w osobnym procesie. Nie tworzy konta
systemowego, osobnej roli bazy, izolacji sieci ani piaskownicy systemowej.
Uprawnienia procesu i roli bazy pozostają uprawnieniami wywołującego.
Śmierć rodzica i zarządzanie usługą wymagają zewnętrznego nadzorcy procesu;
ten moduł nie zastępuje konfiguracji systemd/kontenera.

Przed uruchomieniem usługowym pozostają osobna rola i konto, ograniczenia
połączeń oraz czasu instrukcji SQL, konfiguracja nadzorcy, retencja metadanych,
kopie i rotacja kluczy oraz odbiór dostawcy i DNS. Nie podłączono procesu
do aplikacji ani prawdziwej poczty.

Testy lokalne: ograniczenie partii, pusta kolejka, zatrzymanie przed połączeniem,
przerwanie po trwałym zapisie rozpoczęcia, odzyskanie jako uncertain,
tłumienie prywatnych danych, błąd transportu i serializacji, sprzątanie dzieci
oraz walidacja raportu. Natywna bramka PostgreSQL zawiera osobny scenariusz
uruchomienia spawn z ograniczoną rolą i sztucznym transportem.
