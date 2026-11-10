# WiejskaPaka — pakiet 43–47

Rozszerzono ponowną weryfikację sesji we wspólnej transakcji PostgreSQL na siedem operacji POST: tworzenie projektu prowizji, projektu dokumentu, wniosku o korektę, zadania eksportu, zapis wyniku walidacji, potwierdzenie zapoznania się z walidacją oraz ręczne uzgodnienie testowych płatności przez administratora.

W PostgreSQL każda z tych operacji korzysta z `order_write_db`, który ponownie weryfikuje token, identyfikator i aktualną rolę użytkownika przed zapisem. Tryb SQLite pozostaje developerski. Zapis wyników walidacji wykonuje wcześniejszy odczyt diagnostyczny poza transakcją zapisu — do dalszego przeglądu spójności.

Testy lokalne: **1319 passed, 3 skipped, 16 subtests passed**. Nie przeprowadzono testów integracyjnych z Neon. Nie włączono RLS ani rzeczywistych płatności, nie wysyła się faktur ani przelewów. Należy nadal sprawdzić inne endpointy, uprawnienia DB oraz spójność transakcyjną.
