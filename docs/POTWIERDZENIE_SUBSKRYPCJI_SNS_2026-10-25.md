# Potwierdzenie subskrypcji HTTPS SNS

Dotychczasowy odbiornik przyjmował wyłącznie Notification. Nowa opcja WP_ENABLE_SES_SUBSCRIPTION_CONFIRMATION=1 pozwala również potwierdzić SubscriptionConfirmation. Domyślnie wyłączona; brak połączeń przy imporcie, prepare i kontroli konfiguracji. Opcja wymaga pozostałych chronionych ustawień odbiornika.

Przed połączeniem wychodzącym weryfikowane są: podpis RSA/SHA256, dokładny temat i przypięty certyfikat, okres ważności certyfikatu, świeżość i podpisane Token oraz SubscribeURL. Kolejność kanoniczna: Message, MessageId, SubscribeURL, Timestamp, Token, TopicArn, Type. Podpisany adres musi odpowiadać regionalnemu HTTPS SNS, akcji ConfirmSubscription, temu samemu tematowi i tokenowi, bez dodatkowych parametrów lub fragmentu.

Żądanie jest rekonstruowane z zatwierdzonego regionu i zweryfikowanego tokenu. Nie pobieramy dowolnego SubscribeURL ani certyfikatu z żądania. Brak proxy z otoczenia i przekierowań; timeout 5 s, odpowiedź do 16 KiB. Sukces wymaga HTTP 200 i XML z prawidłowym ARN subskrypcji tego tematu. Błąd daje 503, bez treści wyjątku, tokenu lub URL w logach. Potwierdzenie nie otwiera połączenia bazy i nie zapisuje blokad odbiorców. UnsubscribeConfirmation pozostaje nieobsługiwane.

Wdrożyć wyłącznie nową wersję odbiornika, po testach i kontroli konfiguracji. Główna aplikacja, SMTP, baza i schemat nie wymagają zmian. W osobnym drop-in odbiornika ustawić WorkingDirectory nowego wydania i Environment=WP_ENABLE_SES_SUBSCRIPTION_CONFIRMATION=1. Po uruchomieniu utworzyć subskrypcję HTTPS dla https://ses-feedback.wiejskapaka.pl/sns/feedback, bez raw message delivery. Sprawdzić status Confirmed w SNS. Nie wyłączać email feedback forwarding przed testem zdarzenia SES i blokady odbiorcy. Po potwierdzeniu można wyłączyć opcję potwierdzania i zrestartować tylko odbiornik; kolejne subskrypcje wymagają ponownego jawnego włączenia.

Źródła: https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message-verify-message-signature.html oraz https://docs.aws.amazon.com/sns/latest/dg/SendMessageToHttp.confirm.html .
