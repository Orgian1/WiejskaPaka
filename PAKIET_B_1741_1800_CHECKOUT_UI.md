# B/1741–B/1800 — bezpieczne ponawianie zakupu w panelu

- Formularz koszyka wysyła `Idempotency-Key` (losowy UUID) do endpointu checkout.
- Gdy żądanie zakończy się błędem sieciowym lub niejasnym wynikiem, następna próba z niezmienionymi danymi używa tego samego klucza. Zmiana danych jest blokowana do rozstrzygnięcia poprzedniej próby.
- Po odpowiedzi sukcesu klucz jest czyszczony. Po zmianie konta także jest czyszczony.
- Wynik wyświetla wspólny PIN przesyłki, a nie nieistniejące pola PIN przy każdej pozycji.
- Mechanizm jest w pamięci karty: po odświeżeniu strony nie da się automatycznie wznowić starego klucza. Przed kolejną próbą należy sprawdzić historię zamówień.
- Tryb testowy; brak podłączenia płatności produkcyjnych i brak zmian Neon.
