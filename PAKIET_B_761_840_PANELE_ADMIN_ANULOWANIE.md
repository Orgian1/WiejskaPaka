# B/761–B/840 — interfejs przesyłek (zakres roboczy)

Zrealizowano: panel administracyjny przesyłek z filtrem statusu, paginacją po 20, podsumowaniem wartości produktów, pojedynczej opłaty dostawy, sumy i symulowanych zwrotów. Panel klienta otrzymał przycisk anulowania całej przesyłki z potwierdzeniem i odświeżeniem widoku. Operacje korzystają z istniejących API i autoryzacji serwera. Brak zmian w Neon, płatnościach produkcyjnych i konfiguracji hostingu.

Ważne: przycisk anulowania jest widoczny także przy przesyłkach, których anulowanie jest zabronione; API zwraca wtedy odmowę. Panel administracyjny nie wykonuje operacji zwrotów — pokazuje wyłącznie wyliczenia testowe. Wciąż wymagane testy E2E przeglądarki i pełna regresja.
