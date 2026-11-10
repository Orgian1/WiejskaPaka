"""Polityka komunikacji WiejskaPaka: e-mail i panel, bez SMS i telefonów.

Moduł definiuje kontrakt dla przyszłej integracji dostawcy poczty.
Nie wysyła wiadomości i nie włącza usług produkcyjnych.
"""
from dataclasses import dataclass
from enum import Enum


class Channel(str, Enum):
    EMAIL = "email"
    PANEL = "panel"


class Event(str, Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    ORDER_CONFIRMED = "order_confirmed"
    PICKUP_REMINDER = "pickup_reminder"
    DELIVERY_STATUS = "delivery_status"
    SELLER_NEW_ORDER = "seller_new_order"
    PICKUP_PIN = "pickup_pin"


@dataclass(frozen=True)
class NotificationRule:
    channels: frozenset[Channel]
    requires_verified_email: bool = True


RULES = {
    Event.EMAIL_VERIFICATION: NotificationRule(frozenset({Channel.EMAIL}), False),
    Event.PASSWORD_RESET: NotificationRule(frozenset({Channel.EMAIL}), False),
    Event.ORDER_CONFIRMED: NotificationRule(frozenset({Channel.EMAIL, Channel.PANEL})),
    Event.PICKUP_REMINDER: NotificationRule(frozenset({Channel.EMAIL, Channel.PANEL})),
    Event.DELIVERY_STATUS: NotificationRule(frozenset({Channel.EMAIL, Channel.PANEL})),
    Event.SELLER_NEW_ORDER: NotificationRule(frozenset({Channel.EMAIL, Channel.PANEL})),
    Event.PICKUP_PIN: NotificationRule(frozenset({Channel.EMAIL, Channel.PANEL})),
}


def allowed_channels(event: Event | str, *, email_verified: bool) -> frozenset[Channel]:
    """Nie pozwalaj wysłać zdarzenia nieznanego ani na niezatwierdzony kanał."""
    try:
        rule = RULES[Event(event)]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("Nieznane zdarzenie powiadomienia") from exc
    if rule.requires_verified_email and not email_verified:
        return frozenset({channel for channel in rule.channels if channel is Channel.PANEL})
    return rule.channels


def validate_channel(event: Event | str, channel: Channel | str, *, email_verified: bool) -> None:
    """Fail-closed: SMS, telefon i nieznane kanały zawsze są odrzucane."""
    try:
        selected = Channel(channel)
    except (ValueError, TypeError) as exc:
        raise ValueError("Niedozwolony kanał powiadomienia") from exc
    if selected not in allowed_channels(event, email_verified=email_verified):
        raise ValueError("Kanał niedozwolony dla zdarzenia lub niezweryfikowanego e-maila")
