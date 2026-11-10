# Potwierdzanie adresu konta — przygotowanie prywatnego modułu

Użytkownik potwierdził domenę wiejskapaka.pl w Amazon SES. Potwierdzenie domeny
nie jest dowodem własności skrzynki klienta.

`backend/email_ownership.py` dodaje osobny rejestr dowodów własności adresu:
- wydanie tokenu tylko dla uwierzytelnionego konta (tożsamość musi ustalić przyszły endpoint);
- token losowy 256 bitów, w bazie wyłącznie SHA256; ważność 15 minut;
- ponowne wydanie najwcześniej po 60 sekundach, unieważnia poprzedni token;
- potwierdzenie wymaga zarówno tożsamości konta, jak i sekretu z wiadomości;
- jednokrotne użycie usuwa skrót tokenu;
- powiązanie z adresem aktualnie zapisanym w users;
- blokada rekordu konta w PostgreSQL, obowiązkowa transakcja zapisu;
- odczyt `verified_recipient` jest zaufanym callbackiem kolejki zamówień.

Testy obejmują izolację kont, niepoprawny i wygasły token, zmianę adresu,
wycofanie transakcji, ponowne wydanie oraz prawdziwe połączenie rejestru
z kolejką istniejącego zamówienia. Transport SMTP w testach jest zastąpiony.

## Ograniczenia tego etapu

Nie dodano endpointów HTTP, wysyłki linku, zmian panelu ani migracji instalowanej
na serwerze. Rejestr jest tworzony wyłącznie w jawnych testach SQLite. Nie włączono
wysyłania ani automatycznego pracownika. Nowy moduł nie był jeszcze testowany
na rzeczywistym PostgreSQL; przed integracją trzeba dodać migrację i testy natywne.

Przed uruchomieniem trzeba zbudować uwierzytelnione endpointy z trwałymi limitami
na konto, IP i całą usługę; prywatną kolejkę wiadomości weryfikacyjnych; bezpieczną
obsługę linku w panelu; unieważnianie dowodów przy każdej zmianie adresu (również
przy zmianie z powrotem na poprzedni) i odtwarzaniu kopii; oraz powiązać zapis
zamówienia i jego wiadomości jedną transakcją. Nie wolno zwracać tokenu w API,
logach ani w publicznej skrzynce testowej. Potwierdzenie domeny SES nie zastępuje
tych kroków. Produkcyjny SMTP wymaga osobnych danych dostępu przechowywanych poza kodem.

VPS pozostaje bez zmian. Pełna regresja poprzedniego etapu ma osobny przebieg CI;
nowa gałąź nie powinna go anulować.
