# Prywatne wersjonowane klucze kolejki

Stan: 19.10.2026. Osobny moduł reset_mail_keys odczytuje klucze dla KeyRing.
Nie jest podłączony do aplikacji ani procesu w tle. Nie generuje kluczy,
nie zapisuje plików, nie wykonuje połączeń i niczego nie odczytuje przy imporcie.

load_config(environ) domyślnie zwraca None. Dopiero jawny wpis
WP_ENABLE_MAIL_QUEUE=1 pozwala mu odczytać ścieżkę WP_MAIL_QUEUE_KEYS_FILE.
Samo ustawienie tych zmiennych nie uruchamia wysyłki lub pracownika: żadna
trasa aplikacji nie wywołuje loadera. load_keys(path) służy jawnym wywołaniom.

Plik musi mieć bezwzględną ścieżkę poza projektem, należeć do użytkownika
procesu i nie mieć praw grupy lub innych użytkowników (np. 0600 lub 0400).
Odrzucane są dowiązanie pliku, katalog, FIFO i plik większy od 16 KiB.
Weryfikacja właściciela i uprawnień dotyczy otwartego deskryptora.
Windows ACL nie są odbierane: rzeczywisty odczyt kluczy wymaga POSIX.
Deskryptor jest zamykany także przy odrzuceniu pliku.

Format JSON ma dokładnie trzy pola: format jako całkowite 1, active jako
identyfikator aktywnej wersji i keys jako mapa identyfikatorów na klucze
zakodowane kanonicznym Base64. Każdy klucz ma dokładnie 32 losowe bajty;
przechowywać od jednej do ośmiu różnych wersji, z identyfikatorami zgodnymi
z KeyRing. Identyfikator active musi istnieć. Nie podawać klucza sejfu zamówień
ani hasła SMTP. Nie umieszczać rzeczywistych kluczy w repozytorium, wiadomościach,
raportach, logach lub konfiguracji publicznej. Testy używają tylko sztucznych danych.

Odrzucane są powtórzone nazwy pól JSON, nieznane pola, powtórzone wartości
kluczy i nieprawidłowe kodowanie. Wszystkie odmowy zwracają wyłącznie stały
MAIL_QUEUE_KEYS_REJECTED, bez ścieżki, fragmentu pliku lub szczegółów parsera.
Brak konfiguracji nie powoduje utworzenia zastępczego klucza po restarcie.

Rotacja: prywatnie dodać nowy klucz z nowym identyfikatorem, zachować starsze
wersje potrzebne do oczekujących zadań i zmienić active. Nowe zadania korzystają
z aktywnej wersji, istniejące odczytywane są według zapisanego key_id. Test
potwierdza odczyt wcześniejszego zadania po ponownym załadowaniu dwóch wersji.
Nie usuwać starej wersji, dopóki potrzebują jej zadania lub zachowywane kopie.

Ten etap realizuje odczyt i walidację, nie pełny cykl operacyjny zarządzania
sekretami. Pozostają prywatne przygotowanie kluczy, bezpieczna ich wymiana,
objęcie kopią i testem odtworzenia, integracja pracownika, retencja metadanych
oraz obsługa utraty klucza. Dotychczasowa kopia PostgreSQL z kluczem sejfu
nie stanowi kopii wersjonowanych kluczy poczty. Odtworzenie danych nie może
samodzielnie uruchamiać wysyłki historycznych zadań.
