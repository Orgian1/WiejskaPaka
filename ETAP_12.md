# Etap 12 — endpoint aktywnych adresów dostawcy

Dodano `GET /couriers/me/active-addresses` w FastAPI. Trasa wymaga sesji Bearer sprawdzanej przez `current_user` i roli `dostawca`. Zapytanie filtruje po ID zalogowanego kuriera, statusie `w_drodze_testowo`, rodzaju dostawy i braku potwierdzenia PIN. Nie zwraca telefonu ani e-maila.

Nowe testy: **3/3 zaliczone**.

Pełny zestaw testów lokalnych: **1260 zaliczonych, 5 niezaliczonych, 3 pominięte**. Niezaliczone testy dotyczą wcześniejszych rozbieżności w oczekiwaniach dostępu do lokalizacji i statusów dostawy. Nie należy uznawać aplikacji za gotową do publikacji. Testu połączenia z prywatną bazą Neon nie przeprowadzono. RLS w bazie nadal wyłączony. Płatności wyłącznie testowe.

Nie zmieniano publicznej strony ani bazy Neon.
