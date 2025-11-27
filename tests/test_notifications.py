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
            "appointments": [
                {
                    "dayAbbr": "28 novembre",
                    "startTime": "11:15",
                    "officePlaceName": "Test Clinic A",
                    "examTypeName": "IRM GENERAL",
                    "examName": "IRM Brain",
                },
                {
                    "dayAbbr": "29 novembre",
                    "startTime": "14:30",
                    "officePlaceName": "Test Clinic B",
                    "examTypeName": "IRM GENERAL",
                    "examName": "IRM Brain",
                },
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
        # Structure: header block, exam details block, slots block, metadata block
        self.assertGreaterEqual(len(blocks), 3)
        self.assertLessEqual(len(blocks), 4)

        # Verify first section (header + message)
        self.assertEqual(blocks[0]["type"], "section")
        header_text = blocks[0]["text"]["text"]
        self.assertIn("IRM Appointment Slots Available!", header_text)
        self.assertIn("Found 2 available appointment slot(s)!", header_text)

        # Verify last section (metadata with count and time)
        self.assertEqual(blocks[-1]["type"], "section")
        metadata_text = blocks[-1]["text"]["text"]
        self.assertIn("*Total Slots:*", metadata_text)
        self.assertIn("2", metadata_text)
        self.assertIn("*Time:*", metadata_text)

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
            "appointments": [
                {
                    "dayAbbr": "30 novembre",
                    "startTime": "09:00",
                    "officePlaceName": "Test Clinic",
                    "examTypeName": "IRM GENERAL",
                    "examName": "IRM Brain",
                },
            ],
        }

        notification_service.send(
            "Found 1 available appointment slot(s)!",
            availability_data
        )

        mock_slack_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs
        blocks = call_kwargs["blocks"]

        # Verify slot count in metadata block (last block)
        self.assertGreaterEqual(len(blocks), 3)
        metadata_text = blocks[-1]["text"]["text"]
        self.assertIn("*Total Slots:*", metadata_text)
        self.assertIn("1", metadata_text)

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

        # Create 8 available slots with appointments
        slots = [
            f"Day {i} {9+i}:00" for i in range(1, 9)
        ]

        appointments = [
            {
                "dayAbbr": f"Day {i}",
                "startTime": f"{9+i}:00",
                "officePlaceName": f"Clinic {i}",
                "examTypeName": "IRM GENERAL",
                "examName": "IRM Brain",
            }
            for i in range(1, 9)
        ]

        availability_data = {
            "availabilityCount": 8,
            "availabilityLines": slots,
            "appointments": appointments,
        }

        notification_service.send(
            "Found 8 available appointment slot(s)!",
            availability_data
        )

        mock_slack_client.chat_postMessage.assert_called_once()
        call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs
        blocks = call_kwargs["blocks"]

        # Verify slots are shown in some block
        all_block_text = "\n".join([block["text"]["text"] for block in blocks])
        # Should show some of the slots
        for i in range(1, 4):
            self.assertIn(f"Day {i}", all_block_text)

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
            {
                "availabilityCount": 1,
                "availabilityLines": ["2024-02-01 10:00"],
                "appointments": [
                    {
                        "dayAbbr": "2024-02-01",
                        "startTime": "10:00",
                        "officePlaceName": "Test Clinic",
                        "examTypeName": "IRM GENERAL",
                        "examName": "IRM Brain",
                    },
                ],
            },
        )

        call_kwargs = mock_slack_client.chat_postMessage.call_args.kwargs
        blocks = call_kwargs["blocks"]

        # Check that timestamp is in the metadata section (last block)
        self.assertGreaterEqual(len(blocks), 3)
        metadata_text = blocks[-1]["text"]["text"]
        self.assertIn("*Time:*", metadata_text)
        # Verify timestamp format (YYYY-MM-DD HH:MM:SS)
        self.assertRegex(metadata_text, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


if __name__ == "__main__":
    unittest.main()
