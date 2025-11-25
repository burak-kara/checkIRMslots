import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

# Ensure the src directory is importable when running the test module directly.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from notifications import NotificationService  # noqa: E402


class SlackNotificationTests(unittest.TestCase):
    """Tests for Slack notification functionality."""

    @patch("notifications.WebClient")
    def test_sends_slack_notification_when_slots_found(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that a properly formatted Slack message is sent when appointments are found."""
        # Setup
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client

        mock_slack_client.chat_postMessage.return_value = {"ok": True}

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456789",
            enabled=True
        )

        availability_data = {
            "availabilityCount": 2,
            "availabilityLines": [
                "28 novembre 11:15",
                "29 novembre 14:30",
            ],
        }

        # Execute
        notification_service.send(
            "Found 2 available appointment slot(s)!",
            availability_data
        )

        # Verify Slack API was called with correct parameters
        mock_slack_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs

        # Verify channel and message
        self.assertEqual(call_kwargs["channel"], "C123456789")
        self.assertEqual(call_kwargs["text"], "Found 2 available appointment slot(s)!")

        # Verify blocks structure
        blocks = call_kwargs["blocks"]
        self.assertEqual(len(blocks), 4)  # header, section with message, fields section, slots section

        # Verify header
        self.assertEqual(blocks[0]["type"], "header")
        self.assertEqual(blocks[0]["text"]["text"], "🏥 IRM Appointment Slots Available!")

        # Verify message section
        self.assertEqual(blocks[1]["type"], "section")
        self.assertIn("Found 2 available appointment slot(s)!", blocks[1]["text"]["text"])

        # Verify fields section (slots found and time)
        self.assertEqual(blocks[2]["type"], "section")
        fields = blocks[2]["fields"]
        self.assertEqual(len(fields), 2)
        self.assertIn("2", fields[0]["text"])  # Slots count
        self.assertIn("Time:", fields[1]["text"])

        # Verify availability lines section
        self.assertEqual(blocks[3]["type"], "section")
        availability_text = blocks[3]["text"]["text"]
        self.assertIn("28 novembre 11:15", availability_text)
        self.assertIn("29 novembre 14:30", availability_text)

    @patch("notifications.WebClient")
    def test_slack_message_with_single_slot(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test Slack message formatting with a single appointment."""
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client
        mock_slack_client.chat_postMessage.return_value = {"ok": True}

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456789",
            enabled=True
        )

        availability_data = {
            "availabilityCount": 1,
            "availabilityLines": ["30 novembre 09:00"],
        }

        notification_service.send(
            "Found 1 available appointment slot(s)!",
            availability_data
        )

        mock_slack_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs
        blocks = call_kwargs["blocks"]

        # Verify slot count in fields
        fields = blocks[2]["fields"]
        self.assertIn("1", fields[0]["text"])

    @patch("notifications.WebClient")
    def test_slack_message_with_many_slots_shows_truncation(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that many slots are truncated at 5 with a 'and X more' message."""
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client
        mock_slack_client.chat_postMessage.return_value = {"ok": True}

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456789",
            enabled=True
        )

        # Create 8 available slots
        slots = [
            f"Day {i} {9+i}:00" for i in range(1, 9)
        ]

        availability_data = {
            "availabilityCount": 8,
            "availabilityLines": slots,
        }

        notification_service.send(
            "Found 8 available appointment slot(s)!",
            availability_data
        )

        mock_slack_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs
        blocks = call_kwargs["blocks"]

        # Verify truncation message in availability section
        availability_text = blocks[3]["text"]["text"]
        # Should show first 5 slots
        for i in range(1, 6):
            self.assertIn(f"Day {i}", availability_text)
        # Should show truncation message
        self.assertIn("and 3 more", availability_text)

    @patch("notifications.WebClient")
    def test_slack_notification_handles_api_error(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that Slack API errors are caught and logged."""
        from slack_sdk.errors import SlackApiError

        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client

        # Simulate Slack API error
        error_response = MagicMock()
        error_response.__getitem__ = MagicMock(return_value="invalid_channel")
        slack_error = SlackApiError("error", response=error_response)
        mock_slack_client.chat_postMessage.side_effect = slack_error

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456789",
            enabled=True
        )

        # Should not raise exception, but log error
        notification_service.send(
            "Found 1 available appointment slot(s)!",
            {"availabilityCount": 1, "availabilityLines": ["2024-02-01 10:00"]},
        )

        mock_slack_client.chat_postMessage.assert_called_once()

    @patch("notifications.WebClient")
    def test_slack_notification_handles_unexpected_error(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that unexpected errors during Slack notification are caught."""
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client
        mock_slack_client.chat_postMessage.side_effect = Exception("Network timeout")

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456789",
            enabled=True
        )

        # Should not raise exception
        notification_service.send(
            "Found 1 available appointment slot(s)!",
            {"availabilityCount": 1, "availabilityLines": ["2024-02-01 10:00"]},
        )

        mock_slack_client.chat_postMessage.assert_called_once()

    @patch("notifications.WebClient")
    def test_slack_api_response_ok_false_logged(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that when Slack API returns ok=False, it's properly logged."""
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client

        # Simulate ok=False response from Slack
        mock_slack_client.chat_postMessage.return_value = {
            "ok": False,
            "error": "channel_not_found"
        }

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456789",
            enabled=True
        )

        notification_service.send(
            "Found 1 available appointment slot(s)!",
            {"availabilityCount": 1, "availabilityLines": ["2024-02-01 10:00"]},
        )

        mock_slack_client.chat_postMessage.assert_called_once()

    @patch("notifications.WebClient")
    def test_slack_client_not_initialized_if_no_token(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that WebClient is not initialized if no token is provided."""
        notification_service = NotificationService(
            slack_token=None,
            slack_channel_id="C123456789",
            enabled=True
        )

        # WebClient should not be created if token is None
        mock_webclient_class.assert_not_called()
        self.assertIsNone(notification_service.slack_client)

    @patch("notifications.WebClient")
    def test_no_notification_sent_if_token_missing(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that notification is skipped if Slack token is not configured."""
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client

        notification_service = NotificationService(
            slack_token=None,
            slack_channel_id="C123456789",
            enabled=True
        )

        notification_service.send(
            "Found 1 available appointment slot(s)!",
            {"availabilityCount": 1, "availabilityLines": ["2024-02-01 10:00"]},
        )

        # Slack client should never be called if token is missing
        mock_slack_client.chat_postMessage.assert_not_called()

    @patch("notifications.WebClient")
    def test_no_notification_sent_if_channel_id_missing(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that notification is skipped if Slack channel ID is not configured."""
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id=None,
            enabled=True
        )

        notification_service.send(
            "Found 1 available appointment slot(s)!",
            {"availabilityCount": 1, "availabilityLines": ["2024-02-01 10:00"]},
        )

        # Slack client should never be called if channel ID is missing
        mock_slack_client.chat_postMessage.assert_not_called()

    @patch("notifications.WebClient")
    def test_slack_message_timestamp_included(
        self,
        mock_webclient_class: MagicMock
    ) -> None:
        """Test that the current timestamp is included in Slack message."""
        mock_slack_client = MagicMock()
        mock_webclient_class.return_value = mock_slack_client
        mock_slack_client.chat_postMessage.return_value = {"ok": True}

        notification_service = NotificationService(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456789",
            enabled=True
        )

        notification_service.send(
            "Found 1 available appointment slot(s)!",
            {"availabilityCount": 1, "availabilityLines": ["2024-02-01 10:00"]},
        )

        call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs
        blocks = call_kwargs["blocks"]

        # Check that timestamp is in the fields section
        fields = blocks[2]["fields"]
        time_field = fields[1]["text"]
        self.assertIn("Time:", time_field)
        # Verify timestamp format (YYYY-MM-DD HH:MM:SS)
        self.assertRegex(time_field, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


if __name__ == "__main__":
    unittest.main()
