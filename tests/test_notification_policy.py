"""Regresja polityki powiadomień bez telefonów i SMS."""
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory

from backend.notification_policy import Channel, Event, RULES, allowed_channels, validate_channel


class NotificationPolicyTests(unittest.TestCase):
    def test_only_email_and_panel_are_supported(self):
        self.assertEqual(set(Channel), {Channel.EMAIL, Channel.PANEL})
        self.assertEqual(set(RULES), set(Event))
        for rule in RULES.values():
            self.assertTrue(rule.channels)
            self.assertTrue(rule.channels <= {Channel.EMAIL, Channel.PANEL})

    def test_sms_and_phone_are_rejected_for_every_event(self):
        for event in Event:
            for channel in ("sms", "phone", "telephone", "push", ""):
                with self.subTest(event=event, channel=channel):
                    with self.assertRaises(ValueError):
                        validate_channel(event, channel, email_verified=True)

    def test_pickup_pin_is_only_in_authenticated_panel(self):
        self.assertEqual(allowed_channels(Event.PICKUP_PIN, email_verified=True),
                         frozenset({Channel.PANEL}))
        with self.assertRaises(ValueError):
            validate_channel(Event.PICKUP_PIN, "email", email_verified=True)

    def test_unverified_email_does_not_receive_order_notifications(self):
        self.assertEqual(allowed_channels(Event.ORDER_CONFIRMED, email_verified=False),
                         frozenset({Channel.PANEL}))
        with self.assertRaises(ValueError):
            validate_channel(Event.ORDER_CONFIRMED, "email", email_verified=False)

    def test_verification_and_reset_can_reach_unverified_email(self):
        for event in (Event.EMAIL_VERIFICATION, Event.PASSWORD_RESET):
            validate_channel(event, "email", email_verified=False)

    def test_demo_password_reset_uses_email_policy(self):
        from backend.password_reset import deliver_demo
        with TemporaryDirectory() as folder:
            with patch('backend.password_reset.validate_channel') as check:
                deliver_demo(folder, 'TEST@example.com', 'demo-token')
                check.assert_called_once_with(Event.PASSWORD_RESET, Channel.EMAIL,
                                              email_verified=False)

    def test_unknown_events_fail_closed(self):
        with self.assertRaises(ValueError):
            allowed_channels("marketing_campaign", email_verified=True)
        with self.assertRaises(ValueError):
            validate_channel("marketing_campaign", "email", email_verified=True)


if __name__ == "__main__":
    unittest.main()
