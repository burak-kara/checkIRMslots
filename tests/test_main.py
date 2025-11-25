import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import requests

# Ensure the src directory is importable when running the test module directly.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from auth import SessionCookies  # noqa: E402
from main import Config, IRMSlotChecker  # noqa: E402


class IRMSlotCheckerAvailabilityTests(unittest.TestCase):
    def create_config(self, **overrides: object) -> Config:
        base_config = {
            "api_url": "https://www.easydoct.com/api/rdv/getRdvDayAvailabilities",
            "session_key": "session",
            "user_session_key": "user_session",
            "aspnet_cookies": "aspnet",
            "exam_type_id": "exam_type",
            "exam_id": "exam_id",
            "patient_birth_date": "1990-01-01",
            "poll_interval": 60,
            "log_level": "INFO",
            "log_file": "test.log",
            "notifications_enabled": True,
            "slack_token": "token",
            "slack_channel_id": "channel",
        }
        base_config.update(overrides)
        return Config(**base_config)

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_returns_true_and_sends_notification_when_slots_available(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock
    ) -> None:
        config = self.create_config()
        checker = IRMSlotChecker(config)

        availability_payload = {
            "availabilityCount": 2,
            "availabilityLines": ["2024-02-01 10:00", "2024-02-01 11:00"],
        }

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = availability_payload
        mock_post.return_value = response

        result = checker.check_availability()

        self.assertTrue(result)
        mock_post.assert_called_once()
        called_kwargs = mock_post.call_args.kwargs
        self.assertEqual(called_kwargs["headers"], config.get_headers())
        self.assertEqual(called_kwargs["json"], config.get_payload())

        mock_notification_service.return_value.send.assert_called_once_with(
            "Found 2 available appointment slot(s)!",
            availability_payload,
        )

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_returns_true_for_example_appointments_response(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock
    ) -> None:
        config = self.create_config()
        checker = IRMSlotChecker(config)

        example_response = {
            "appointments": [
                "None",
                "None",
                {
                    "dayAbbr": "28 novembre",
                    "startTime": "11:15",
                    "roomName": "IRM CANOPIA",
                },
                "None",
            ]
        }

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = example_response
        mock_post.return_value = response

        result = checker.check_availability()

        self.assertTrue(result)
        mock_notification_service.return_value.send.assert_called_once_with(
            "Found 1 available appointment slot(s)!",
            {
                **example_response,
                "availabilityCount": 1,
                "availabilityLines": ["28 novembre 11:15"],
            },
        )

    @patch("main.get_session_cookies")
    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_auto_login_then_finds_slots_after_authentication_error(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock,
        mock_get_session_cookies: MagicMock
    ) -> None:
        config = self.create_config(
            auto_login_enabled=True,
            easydoct_email="user@example.com",
            easydoct_password="secret",
            exam_url="https://www.easydoct.com/rdv/example",
        )
        initial_headers = config.get_headers()

        mock_get_session_cookies.return_value = SessionCookies(
            session_key="new_session",
            user_session_key="new_user_session",
            aspnet_cookies="new_aspnet",
        )

        auth_error_response = MagicMock()
        auth_error_response.status_code = 401
        auth_error_response.json.return_value = {}

        availability_payload = {
            "availabilityCount": 1,
            "availabilityLines": ["2024-03-10 09:00"],
        }
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = availability_payload

        mock_post.side_effect = [auth_error_response, success_response]

        checker = IRMSlotChecker(config)
        result = checker.check_availability()

        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 2)

        first_call_headers = mock_post.call_args_list[0].kwargs["headers"]
        second_call_headers = mock_post.call_args_list[1].kwargs["headers"]

        self.assertEqual(first_call_headers["Cookie"], initial_headers["Cookie"])
        self.assertEqual(
            second_call_headers["Cookie"],
            "SessionKey=new_session; UserSessionKey=new_user_session; .AspNet.Cookies=new_aspnet",
        )

        mock_get_session_cookies.assert_called_once_with(
            email="user@example.com",
            password="secret",
            exam_url="https://www.easydoct.com/rdv/example",
        )

        mock_notification_service.return_value.send.assert_called_once_with(
            "Found 1 available appointment slot(s)!",
            availability_payload,
        )

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_no_slots_available_does_not_send_notification(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock
    ) -> None:
        config = self.create_config()
        checker = IRMSlotChecker(config)

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"availabilityCount": 0, "appointments": []}
        mock_post.return_value = response

        result = checker.check_availability()

        self.assertFalse(result)
        mock_notification_service.return_value.send.assert_not_called()

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_notification_disabled_does_not_send_slack_message(
        self,
        mock_post: MagicMock,
        mock_notification_service_class: MagicMock
    ) -> None:
        """Verify NotificationService is initialized with enabled=False when notifications_enabled=False."""
        config = self.create_config(notifications_enabled=False)
        checker = IRMSlotChecker(config)

        availability_payload = {
            "availabilityCount": 1,
            "availabilityLines": ["2024-02-01 10:00"],
        }

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = availability_payload
        mock_post.return_value = response

        result = checker.check_availability()

        self.assertTrue(result)
        # Verify NotificationService was initialized with enabled=False
        # (tokens are still passed even when notifications are disabled)
        call_args = mock_notification_service_class.call_args
        self.assertEqual(call_args.kwargs['enabled'], False)

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_notification_service_initialized_correctly(
        self,
        mock_post: MagicMock,
        mock_notification_service_class: MagicMock
    ) -> None:
        config = self.create_config(
            notifications_enabled=True,
            slack_token="xoxb-test-token",
            slack_channel_id="C123456"
        )
        checker = IRMSlotChecker(config)

        # Verify NotificationService was initialized with correct parameters
        mock_notification_service_class.assert_called_once_with(
            slack_token="xoxb-test-token",
            slack_channel_id="C123456",
            enabled=True
        )

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_request_error_returns_false(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock
    ) -> None:
        config = self.create_config()
        checker = IRMSlotChecker(config)

        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        result = checker.check_availability()

        self.assertFalse(result)
        mock_notification_service.return_value.send.assert_not_called()

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_handles_403_forbidden_error(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock
    ) -> None:
        config = self.create_config()
        checker = IRMSlotChecker(config)

        response = MagicMock()
        response.status_code = 403
        response.json.return_value = {}
        mock_post.return_value = response

        result = checker.check_availability()

        self.assertFalse(result)
        mock_notification_service.return_value.send.assert_not_called()

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_multiple_appointments_logged(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock
    ) -> None:
        config = self.create_config()
        checker = IRMSlotChecker(config)

        availability_payload = {
            "availabilityCount": 5,
            "availabilityLines": [
                "28 novembre 11:15",
                "29 novembre 09:30",
                "29 novembre 14:00",
                "30 novembre 10:00",
                "1 décembre 15:30"
            ],
        }

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = availability_payload
        mock_post.return_value = response

        result = checker.check_availability()

        self.assertTrue(result)
        mock_notification_service.return_value.send.assert_called_once_with(
            "Found 5 available appointment slot(s)!",
            availability_payload,
        )

    @patch("main.NotificationService")
    @patch("main.requests.post")
    def test_slack_notification_formatting(
        self,
        mock_post: MagicMock,
        mock_notification_service: MagicMock
    ) -> None:
        """Verify the notification message is formatted correctly with slot count."""
        config = self.create_config()
        checker = IRMSlotChecker(config)

        test_cases = [
            (1, "Found 1 available appointment slot(s)!"),
            (2, "Found 2 available appointment slot(s)!"),
            (10, "Found 10 available appointment slot(s)!"),
        ]

        for availability_count, expected_message in test_cases:
            with self.subTest(count=availability_count):
                availability_payload = {
                    "availabilityCount": availability_count,
                    "availabilityLines": ["2024-02-01 10:00"],
                }

                response = MagicMock()
                response.status_code = 200
                response.json.return_value = availability_payload
                mock_post.return_value = response

                result = checker.check_availability()

                self.assertTrue(result)
                mock_notification_service.return_value.send.assert_called_with(
                    expected_message,
                    availability_payload,
                )
                mock_notification_service.return_value.send.reset_mock()


if __name__ == "__main__":
    unittest.main()
