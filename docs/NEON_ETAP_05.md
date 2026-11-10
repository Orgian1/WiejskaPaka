# Neon — etap 05: kontekst tożsamości do przyszłego RLS

Dodano `backend/neon_identity.py` i testy. Funkcja `authenticated_actor` przyjmuje **wyłącznie identyfikator ustalony po serwerowej weryfikacji sesji**. Ustawia parametr PostgreSQL przez parametryzowane `set_config(..., true)` (zakres transakcji), a po użyciu go czyści. Należy wywoływać ją wewnątrz tej samej transakcji co chronione zapytania.

**To nie jest jeszcze włączone zabezpieczenie RLS.** Nie zmieniono produkcyjnych tabel ani uprawnień. Nie należy uznawać samych zmiennych `current_setting` za bezpieczne przy koncie SQL, które może dowolnie ustawiać kontekst; docelowo trzeba przeanalizować architekturę zaufania, uprawnienia, właściciela tabel i polityki oraz testować je z realną bazą. Aplikacja nadal wymaga weryfikacji uprawnień po stronie serwera.

Kolejny krok: podłączenie pomocnika do zweryfikowanej sesji backendu, a następnie przygotowanie i testowanie polityk na osobnej bazie testowej. Nie włączać RLS na żywej bazie przed tym etapem. Hasła i DATABASE_URL pozostają poza kodem i rozmową.
