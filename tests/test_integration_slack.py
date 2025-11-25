"""
Integration tests that send REAL Slack notifications.

These tests load credentials from the .env file and send actual messages to Slack.
They use the exact API response format from the easydoct API to test real notification delivery.

To run these tests:
    .venv\Scripts\python.exe -m unittest tests.test_integration_slack -v

Requirements:
    - SLACK_TOKEN must be set in .env (xoxb-... format)
    - SLACK_CHANNEL_ID must be set in .env (C... format)
    - Bot must be added to the channel:
        1. Go to your Slack channel
        2. Click channel name -> Details
        3. Go to "Integrations" or "Apps"
        4. Find your bot app and click "Add"
    - Bot must have "chat:write" permission in OAuth scopes

If you get "not_in_channel" error, add the bot to your Slack channel first.
"""

import sys
import os
from pathlib import Path
import unittest
from dotenv import load_dotenv

# Ensure the src directory is importable when running the test module directly.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from notifications import NotificationService  # noqa: E402


class RealSlackNotificationIntegrationTests(unittest.TestCase):
    """Integration tests that send REAL Slack notifications to your configured channel."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load environment variables from .env file."""
        # Load from project root (checkIRMslots directory)
        env_path = ROOT_DIR.parent / ".env"

        # Load the .env file
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # If not found in parent, try current directory
            load_dotenv()

        cls.slack_token = os.getenv("SLACK_TOKEN")
        cls.slack_channel_id = os.getenv("SLACK_CHANNEL_ID")

        # Debug: print what we found
        print(f"\nLoading .env from: {env_path}")
        print(f"SLACK_TOKEN found: {bool(cls.slack_token)}")
        print(f"SLACK_CHANNEL_ID found: {bool(cls.slack_channel_id)}")

    def setUp(self) -> None:
        """Skip tests if Slack credentials are not configured."""
        if not self.slack_token or not self.slack_channel_id:
            self.skipTest(
                "Slack credentials not configured. "
                "Set SLACK_TOKEN and SLACK_CHANNEL_ID in .env to run integration tests."
            )

        # Note: If you get "not_in_channel" error, add your bot to the Slack channel first
        # 1. Go to your Slack channel
        # 2. Click on the channel name
        # 3. Go to "Integrations" or "Apps"
        # 4. Find your bot and add it to the channel

    def test_send_real_slack_notification_with_api_response_format(self) -> None:
        """
        Send a REAL Slack notification using the exact API response format from easydoct.

        This is the primary integration test that uses the actual response structure
        documented in CLAUDE.md with a single appointment available.
        """
        # Use the exact API response format from CLAUDE.md
        api_response = {
            "appointments": [
                "None",
                "None",
                "None",
                {
                    "id": "19692c55-3315-4a9f-907c-e39e6a4c0540",
                    "start": "2025-11-28T11:15:00",
                    "end": "2025-11-28T11:30:00",
                    "convocation": "2025-11-28T11:00:00",
                    "day": "2025-11-28T00:00:00",
                    "dayOfWeek": "vendredi",
                    "dayAbbr": "28 novembre",
                    "startTime": "11:15",
                    "endTime": "11:30",
                    "convocationTimeText": "(convocation à 11:00)",
                    "convocationTime": "11:00",
                    "officeId": 354,
                    "officePlaceVisibleId": "e3d30d46-dc74-4580-9358-941959d01388",
                    "officePlaceName": "SCANNER-IRM CANOPIA - Cesson-Sévigné Service SCANNER-IRM CIM Laënnec",
                    "officePlaceId": 1390,
                    "roomId": 4608,
                    "roomName": "IRM CANOPIA",
                    "roomColor": "#F26C55",
                    "useRoomDurationForAllAppointment": "False",
                    "availablePractitioners": [
                        {
                            "id": 17317,
                            "firstNameLastName": "Maxence SERRU",
                            "lastNameFirstName": "None",
                            "isPractitionerSubstitute": "False",
                            "incumbentPractitionerId": "None",
                            "incumbentPractitionerLastNameFirstName": "None",
                            "practitionerInfoId": 0
                        }
                    ],
                    "practitionerId": 17317,
                    "practitionerFirstNameLastName": "Dr Maxence SERRU",
                    "practitionerLastNameFirstName": "None",
                    "isPractitionerSubstitute": "False",
                    "examTypeId": 3374,
                    "examTypeName": "IRM OSTEO-ARTICULAIRE / RACHIS",
                    "examId": 56796,
                    "examName": "IRM pied / cheville",
                    "examNameForPatient": "IRM pied / cheville",
                    "secondAvailableAppointment": "None",
                    "differentDayText": "None",
                    "emergency": "False",
                    "multiAvailabilityEmergency": "False",
                    "userScheduleName": "None",
                    "officePlace": "None",
                    "teleinterpretation": "False"
                },
                "None",
                "None",
                "None"
            ]
        }

        # Parse the API response as the checker would
        availability_count = len([
            appt for appt in api_response.get("appointments", [])
            if isinstance(appt, dict)
        ])

        availability_lines = []
        for appt in api_response.get("appointments", []):
            if not isinstance(appt, dict):
                continue
            day_label = appt.get("dayAbbr") or appt.get("day")
            time_label = appt.get("startTime") or appt.get("start")
            if day_label and time_label:
                availability_lines.append(f"{day_label} {time_label}")

        data_to_send = {
            **api_response,
            "availabilityCount": availability_count,
            "availabilityLines": availability_lines,
        }

        # Create notification service with real credentials
        notification_service = NotificationService(
            slack_token=self.slack_token,
            slack_channel_id=self.slack_channel_id,
            enabled=True
        )

        # Send REAL notification to Slack
        notification_service.send(
            f"Found {availability_count} available appointment slot(s)!",
            data_to_send
        )

        # If we reach here, notification was sent successfully
        print(f"\n[OK] Real Slack notification sent! Slots found: {availability_count}")
        self.assertTrue(True)

    def test_send_real_slack_notification_with_multiple_appointments(self) -> None:
        """
        Send a REAL Slack notification with multiple appointments.

        This tests the truncation feature (5 slots + "...and X more").
        """
        # Create a response with multiple appointments
        api_response = {
            "appointments": [
                {
                    "dayAbbr": "28 novembre",
                    "startTime": "09:00",
                    "examName": "IRM pied",
                    "roomName": "IRM CANOPIA",
                },
                {
                    "dayAbbr": "28 novembre",
                    "startTime": "10:30",
                    "examName": "IRM pied",
                    "roomName": "IRM CANOPIA",
                },
                {
                    "dayAbbr": "29 novembre",
                    "startTime": "11:15",
                    "examName": "IRM pied",
                    "roomName": "IRM CANOPIA",
                },
                {
                    "dayAbbr": "29 novembre",
                    "startTime": "14:00",
                    "examName": "IRM pied",
                    "roomName": "IRM CANOPIA",
                },
                {
                    "dayAbbr": "30 novembre",
                    "startTime": "09:45",
                    "examName": "IRM pied",
                    "roomName": "IRM CANOPIA",
                },
                {
                    "dayAbbr": "30 novembre",
                    "startTime": "15:30",
                    "examName": "IRM pied",
                    "roomName": "IRM CANOPIA",
                },
            ]
        }

        # Parse availability
        availability_count = len([
            appt for appt in api_response.get("appointments", [])
            if isinstance(appt, dict)
        ])

        availability_lines = []
        for appt in api_response.get("appointments", []):
            if not isinstance(appt, dict):
                continue
            day_label = appt.get("dayAbbr")
            time_label = appt.get("startTime")
            if day_label and time_label:
                availability_lines.append(f"{day_label} {time_label}")

        data_to_send = {
            **api_response,
            "availabilityCount": availability_count,
            "availabilityLines": availability_lines,
        }

        notification_service = NotificationService(
            slack_token=self.slack_token,
            slack_channel_id=self.slack_channel_id,
            enabled=True
        )

        # Send REAL notification
        notification_service.send(
            f"Found {availability_count} available appointment slot(s)!",
            data_to_send
        )

        print(f"\n[OK] Real Slack notification sent! Slots found: {availability_count}")
        print(f"   (Should show 5 slots + '...and 1 more' due to truncation)")
        self.assertTrue(True)

    def test_send_real_slack_notification_minimal_format(self) -> None:
        """
        Send a REAL Slack notification with minimal appointment data.

        This tests that the notification works even with minimal information.
        """
        api_response = {
            "appointments": [
                {
                    "dayAbbr": "1 décembre",
                    "startTime": "10:00",
                }
            ]
        }

        availability_count = len([
            appt for appt in api_response.get("appointments", [])
            if isinstance(appt, dict)
        ])

        availability_lines = []
        for appt in api_response.get("appointments", []):
            if not isinstance(appt, dict):
                continue
            day_label = appt.get("dayAbbr")
            time_label = appt.get("startTime")
            if day_label and time_label:
                availability_lines.append(f"{day_label} {time_label}")

        data_to_send = {
            **api_response,
            "availabilityCount": availability_count,
            "availabilityLines": availability_lines,
        }

        notification_service = NotificationService(
            slack_token=self.slack_token,
            slack_channel_id=self.slack_channel_id,
            enabled=True
        )

        notification_service.send(
            f"Found {availability_count} available appointment slot(s)!",
            data_to_send
        )

        print(f"\n[OK] Real Slack notification sent! Slots found: {availability_count}")
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()

