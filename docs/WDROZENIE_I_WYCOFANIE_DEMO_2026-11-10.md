# Bezpieczne wdrożenie i wycofanie demo na VPS

Aktualizacja 13.11: dla obecnego pakietu stosuj
[aktualną procedurę odbioru](AKTUALIZACJA_VPS_ODBIOR_2026-11-13.md).
Poniższy dokument opisuje historyczne wydanie; nie uruchamiaj pełnego łańcucha
migracji nowej bazy na istniejącym VPS.

Procedura przygotowana, niewykonana. W tej sesji nie ma zweryfikowanego dostępu
SSH ani stanu VPS. Nie wolno traktować historycznego HTTP 200 jako kontroli
bieżącego wdrożenia. Nie zmieniać działających usług na podstawie samego raportu.

## 1. Odczyt i zabezpieczenie istniejącego stanu

Na właściwym serwerze najpierw odczytać stan, bez aktualizacji kodu:

```bash
systemctl show wiejskapaka-preview -p ActiveState -p MainPID -p FragmentPath -p User -p WorkingDirectory
cd /opt/wiejskapaka/app
git status --short
git rev-parse HEAD
git branch --show-current
curl --fail --silent http://127.0.0.1:8000/health
```

Ścieżki, port i nazwę usługi zweryfikować z rzeczywistą konfiguracją.
Nie publikować konfiguracji środowiska, danych bazy, haseł ani treści kluczy.
Zapisać prywatnie OLD_SHA, wersję Pythona, zależności, konfigurację usług
aplikacji i workerów oraz listę aktywnych flag. Sprawdzić również inne checkouty,
untracked i pliki ignorowane. Nie używać reset --hard, clean ani stash jako backupu.
Niezacommitowane zmiany skopiować do osobnego prywatnego archiwum z listą plików,
uprawnieniami i sumą kontrolną; git diff --binary obejmuje tylko pliki śledzone.
Archiwum może zawierać sekrety, więc nie wolno go wysyłać do repozytorium.

## 2. Spójna kopia i próba przywrócenia

Ustalić, czy działa PostgreSQL czy SQLite. W uzgodnionym oknie technicznym
wstrzymać zapis aplikacji i powiązane workery; zapisać wcześniej stan każdej usługi.
Zachować razem bazę, istniejące klucze sejfu zakupów, klucze kolejek/rotacji,
konfigurację usług i pliki zewnętrzne. Nie generować nowych kluczy do starej bazy.

Dla lokalnej testowej PostgreSQL 16/17 skorzystać z istniejącego szyfrowanego
`python -m scripts.postgres_test_backup backup` oraz `rehearse` zgodnie z
`KOPIA_POSTGRESQL_I_PROBA_ODTWORZENIA.md`. Narzędzia pg_dump i pg_restore muszą
mieć zgodną wersję; limit dumpu wynosi 64 MiB. Klucz kopii przechować oddzielnie.
Narzędzie odmawia baz produkcyjnych i zdalnych: nie omijać tej kontroli.
Dla SQLite stosować istniejącą procedurę snapshot/recovery, nie zwykłe cp
aktywnego pliku pomijające WAL. Test odtworzenia wykonywać w nowej izolowanej
bazie, bez SMTP i bez historycznych aktywnych sesji/tokenów.

Warunek przejścia: rzeczywiście odtworzona kopia, audyt płatności i odczytu
zaszyfrowanych danych zaliczone, komplet kluczy odtwarzalny. Sam plik backupu
nie wystarcza. Jeśli serwer przekracza zakres istniejącego narzędzia, użyć
właściwego mechanizmu backupu operatora i przećwiczyć odtworzenie przed zmianą.

## 3. Nowe wydanie obok starego

Pobrać sprawdzony pełny SHA z gałęzi `codex/demo-finalization-fixes-20261112`
do nowego katalogu wydania. Sprawdzić SHA i brak lokalnych zmian.
Nie wykonywać pull ani checkout w katalogu z niezabezpieczonymi zmianami.
Utworzyć oddzielny venv i zainstalować requirements-lock.txt. Zachować stare
wydanie, jego venv i konfigurację do rollbacku. Kontrola migracji:

```bash
python -m database.verify_test_migrations
```

Pakiety portfela po #51 dodają opcjonalne migracje opisane w
`WYPLATY_DEMO_ETAP2_2026-11-10.md` oraz `ODZYSKIWANIE_OPERACJI_PORTFELA_2026-11-10.md`,
w tym `optional_wallet_operation_fences.sql`. Stosować pełną kolejność manifestu
na odtworzonej kopii; sprawdzić niezmienne warunki wypłat, decyzje i blokady kluczy.
Nie zakładać, że wcześniejsze opcjonalne tabele są już zainstalowane na VPS.
Dla aktywnych flag porównać manifest,
schemat i uprawnienia z bieżącą bazą. Migracje wcześniejszego łańcucha najpierw
uruchomić na odtworzonej kopii. Nie nadawać aplikacji uprawnień administratora.

## 4. Próba na oddzielnym podglądzie

Najbezpieczniej uruchomić nowe wydanie na oddzielnej testowej bazie i porcie,
bez podmieniania starej usługi. Dla trwałego PostgreSQL użyć istniejących
`check_postgres_preview.py`, `check_wallet_integrity.py` oraz
`backend.test_server_launcher`; konfiguracja z `deploy/preview/preview.env.example`
jest wzorem, nie gotowym plikiem z hasłami. Dane przekazywać prywatnie poza repo.
Zachować WP_ENV=test, WP_REAL_PAYMENTS=0 i bind 127.0.0.1. Symulację płatności
włączać wyłącznie w zamkniętym demo. Nie kopiować konfiguracji produkcyjnej PayU.
Nie uruchamiać automatycznie workerów SMTP/SNS. Stan istniejących usług poczty
pozostawić do osobnego, świadomego przełączenia.

Profil `run_phone_demo.py --full-demo` jest jednorazową SQLite do lokalnego odbioru,
a nie migracją ani launcherem trwałej bazy VPS. Zdalny odbiór przez zabezpieczony
tunel SSH; nie wystawiać surowego portu z symulowanymi doładowaniami publicznie.
Sprawdzić health, nagłówek, logowanie/rejestrację, wszystkie role, koszyk,
pojedynczą opłatę dostawy, PIN, powtórzenia operacji, prowizję 5%/0%, raport i CSV,
zwroty oraz telefon/desktop. Sprawdzić brak ponownych wysyłek historycznych zadań.

## 5. Przełączenie i wycofanie

Przełączać wyłącznie po zgodności z kopią, testach i sprawdzeniu bieżącego stanu.
Wzorzec usługi używa stałego /opt/wiejskapaka/app, więc przygotować jawny override
WorkingDirectory/ExecStart/ExecStartPre albo kontrolowany wskaźnik wydania;
nie podmieniać katalogu w ciemno. Zachować poprzedni plik usługi i venv.
Po przełączeniu sprawdzić systemctl is-active, health i powyższy scenariusz.
Błędy schematu, 500, niespójność portfela lub ujawnienie danych oznaczają rollback.

Jeśli wraca kod bez obsługi blokad kluczy operacji albo niezmiennych warunków
wypłat, wyłączyć portfel i jego zapisy przed uruchomieniem starego wydania.
Zachować tabele blokad, warunków i decyzji; ich usunięcie mogłoby dopuścić
ponowne księgowanie starego żądania. Szczegóły zgodności są w obu raportach portfela.

Rollback bez zmiany schematu: zatrzymać nowe wydanie, przywrócić poprzedni wskaźnik kodu,
venv, konfigurację usługi i flagi, uruchomić poprzednią usługę, sprawdzić health.
Nie odtwarzać bazy automatycznie: utraciłoby to nowe operacje. Najpierw zachować
kopię stanu po awarii. Gdy baza była zmieniana, ocenić zgodność wsteczną i użyć
przećwiczonej procedury odtworzenia z kwarantanną starych sesji i zadań pocztowych.
Sprawdzić ponownie klucze, PIN-y, saldo, rezerwacje i zamówienia. Workery włączać
po kontroli stanów, aby uniknąć odtworzenia historycznej wysyłki.
