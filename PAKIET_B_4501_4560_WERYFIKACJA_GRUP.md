# WiejskaPaka B/4501–B/4560 — weryfikacja grup regresji

- Grupa 27: **3/3 moduły PASS**, 6,83 s.
- Grupa 1: **8/8 modułów PASS**, 27,91 s.
- Grupa 2: **1/8 modułów PASS** przed przerwaniem przebiegu z powodu limitu czasu wykonania.
- Raport wcześniejszy obejmuje **166 modułów PASS** (grupy 6–26, ostatnia grupa niepełna).
- Wszystkie trzy raporty mają identyczny odcisk kodu aplikacji i manifestu testów; nie są jednak raportem kompletnej regresji.
- Łącznie w tych rozłącznych zakresach potwierdzono **178/211 modułów** (166 + 3 + 9). Pozostały **33 moduły**: grupy 2–5 (31) i dwa moduły grupy 26.
- Do ukończenia pozostają również rzeczywiste testy PostgreSQL, przeglądarkowe i mobilne, audyt bezpieczeństwa.
- Nie zmieniano konfiguracji Neon, hostingu, domeny ani płatności rzeczywistych.
