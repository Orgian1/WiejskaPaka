# Pakiet B/01 — prywatność interfejsu mobilnego

- Wylogowanie usuwa z pamięci przeglądarki token **przed** próbą powiadomienia serwera. Interfejs nie czeka na odpowiedź sieci.
- Widoki zamówień, punktów odbioru, powiadomień i panelu są czyszczone przy wylogowaniu; formularze gospodarstwa i punktów odbioru są resetowane.
- Odpowiedzi żądań rozpoczętych w poprzedniej sesji są odrzucane po zmianie sesji, co ogranicza ryzyko ponownego pokazania prywatnych danych po wylogowaniu.
- Testy sprawdzają składnię obu skryptów przez Node.js (jeśli dostępny) i obecność ochrony regresyjnej.

**Granice:** to utwardzenie interfejsu, nie zamiennik autoryzacji po stronie API. Nie przeprowadzono manualnych testów na fizycznym telefonie. Nie zmieniono Neon, strony publicznej ani płatności.
