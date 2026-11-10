# B/3361–B/3420 — spójna ochrona zakupu bezpośredniego

- Przycisk „Zamów testowo” na karcie produktu respektuje blokadę nierozstrzygniętego zakupu z koszyka; wcześniej umożliwiał ominięcie zabezpieczenia po odświeżeniu strony.
- Po zmianie sesji w czasie oczekiwania na odpowiedź `/orders` interfejs nie pokazuje numeru zamówienia ani PIN-u poprzedniego użytkownika.
- Dodano testy kontraktowe i uaktualniono starszy test kontraktowy do już istniejącego przypisywania `checkoutOwner`.
- Nie zmieniano bazy Neon, produkcyjnych płatności ani hostingu.
- Nadal potrzebne są pełne testy end-to-end w przeglądarce i regresja po zmianach.
