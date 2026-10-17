# Pakiet B/12 — bezpieczeństwo działań w panelu zamówień

- Przycisk anulowania zamówienia jest blokowany podczas żądania API i odblokowywany również przy błędzie; zapobiega to przypadkowemu wielokrotnemu klikaniu.
- Sześciocyfrowy PIN odbioru jest usuwany z formularza również wtedy, gdy serwer zwróci błąd lub wystąpi problem z połączeniem.
- Dodano dwa testy regresyjne kontrolujące powyższe reguły.

Testy kodu nie zastępują prób w przeglądarce telefonu. Nie zmieniono bazy Neon, domeny ani konfiguracji płatności.
