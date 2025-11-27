import logging
from datetime import datetime
from typing import Dict, Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class NotificationService:
    """Handle Slack notifications for appointment availability."""

    def __init__(
            self,
            slack_token: Optional[str] = None,
            slack_channel_id: Optional[str] = None,
            enabled: bool = True
    ):
        """
        Initialize notification service.

        Args:
            slack_token: Slack Bot User OAuth Token
            slack_channel_id: Slack channel ID to send messages to
            enabled: Whether notifications are enabled
        """
        self.slack_token = slack_token
        self.slack_channel_id = slack_channel_id
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)

        # Initialize Slack client if token is provided
        self.slack_client = WebClient(token=slack_token) if slack_token else None

    def send(self, message: str, availability_data: Dict[str, Any]) -> None:
        """
        Send notification if enabled.

        Args:
            message: The notification message
            availability_data: Full availability data from API response
        """
        if not self.enabled:
            self.logger.info("Notifications disabled, skipping")
            return

        if not self.slack_token or not self.slack_channel_id:
            self.logger.warning("Slack token or channel ID not configured, skipping notification")
            return

        if not self.slack_client:
            self.logger.error("Slack client not initialized")
            return

        self._send_slack(message, availability_data)

    def _extract_exam_details(self, appointments: list) -> Dict[str, str]:
        """Extract exam type and location from appointments."""
        exam_details = {}

        # Find first valid appointment to extract details
        if not appointments:
            return exam_details

        for appt in appointments:
            if isinstance(appt, dict) and appt:
                exam_type = appt.get("examTypeName")
                exam_name = appt.get("examName")
                if exam_type:
                    exam_details["examType"] = exam_type
                if exam_name:
                    exam_details["examName"] = exam_name
                if exam_details:
                    self.logger.debug(f"Extracted exam details: {exam_details}")
                    break

        return exam_details

    def _format_appointment_details(self, appointments: list) -> str:
        """Format appointment details for display."""
        details = []

        # Extract exam details
        exam_details = self._extract_exam_details(appointments)
        if exam_details.get("examType"):
            details.append(f"*Exam Type:* {exam_details['examType']}")
        if exam_details.get("examName"):
            details.append(f"*Exam:* {exam_details['examName']}")

        return "\n".join(details)

    def _flatten_appointments_from_response(self, availability_data: Dict[str, Any]) -> list:
        """Flatten appointments from API response structure (handles both old and new formats)."""
        appointments = []

        # Try direct appointments array first (legacy format)
        if "appointments" in availability_data and isinstance(availability_data["appointments"], list):
            # Filter out None values and string representations
            for appt in availability_data["appointments"]:
                if isinstance(appt, dict) and appt:
                    appointments.append(appt)
            if appointments:
                return appointments

        # Try nested availabilityLines format (current API structure)
        if "availabilityLines" in availability_data and isinstance(availability_data["availabilityLines"], list):
            for line in availability_data["availabilityLines"]:
                if isinstance(line, dict) and "appointments" in line:
                    line_appointments = line.get("appointments", [])
                    if isinstance(line_appointments, list):
                        for appt in line_appointments:
                            # Only add actual dicts, not None or string representations like "None"
                            if isinstance(appt, dict) and appt:
                                appointments.append(appt)

        return appointments

    def _format_slot_list(self, appointments: list, max_slots: int = 20) -> str:
        """Format available slots with datetime and location."""
        slots = []
        count = 0

        if not appointments:
            return ""

        for appt in appointments:
            if not isinstance(appt, dict) or not appt:
                continue

            if count >= max_slots:
                break

            # Extract slot information
            day_abbr = appt.get("dayAbbr", "")
            start_time = appt.get("startTime", "")
            location = appt.get("officePlaceName", "")

            if day_abbr and start_time:
                # Format: "15 janvier 11:15 - Location"
                if location:
                    # Clean up location name
                    location = location.strip()
                    slots.append(f"• {day_abbr} {start_time} - {location}")
                else:
                    slots.append(f"• {day_abbr} {start_time}")
                count += 1

        self.logger.debug(f"Formatted {count} slots for display")
        return "\n".join(slots)

    def _send_slack(self, message: str, availability_data: Dict[str, Any]) -> None:
        """
        Send notification to Slack via API.

        Args:
            message: The notification message
            availability_data: Full availability data from API response
        """
        try:
            # Slack has a 3000-character limit per text block
            SLACK_TEXT_LIMIT = 3000

            # Extract data - handle both old and new API response formats
            appointments = self._flatten_appointments_from_response(availability_data)
            availability_count = availability_data.get("availabilityCount", 0)

            self.logger.debug(f"Building Slack notification with {len(appointments)} flattened appointments")
            self.logger.debug(f"Availability count: {availability_count}")

            # Build formatted message - use only text-based blocks to avoid validation issues
            blocks = []

            # First block: header with count message
            header_text = f":hospital: *IRM Appointment Slots Available!*\n{message}"
            if len(header_text) > SLACK_TEXT_LIMIT:
                header_text = f":hospital: *IRM Appointment Slots Available!*\n{message[:SLACK_TEXT_LIMIT - 40]}"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header_text
                }
            })

            # Second block: appointment type and exam details
            exam_details_text = self._format_appointment_details(appointments)
            if exam_details_text:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": exam_details_text
                    }
                })

            # Third block: available slots list (first 20)
            slots_text = self._format_slot_list(appointments, max_slots=20)
            if slots_text:
                # Build slots block text and handle character limit
                slots_block_text = f"*Available Slots:*\n{slots_text}"

                if len(slots_block_text) > SLACK_TEXT_LIMIT:
                    # If too long, truncate slot list
                    slots_text = self._format_slot_list(appointments, max_slots=5)
                    slots_block_text = f"*Available Slots (showing first 5 of {availability_count}):*\n{slots_text}"

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": slots_block_text
                    }
                })

            # Fourth block: metadata (count and timestamp)
            metadata_text = f"*Total Slots:* {availability_count} | *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": metadata_text
                }
            })

            # Send message using Slack API
            self.logger.debug(f"Sending Slack message with {len(blocks)} blocks")
            response = self.slack_client.chat_postMessage(
                channel=self.slack_channel_id,
                text=message,  # Fallback text for notifications
                blocks=blocks
            )

            if response.get("ok"):
                self.logger.info(f"Slack notification sent successfully to channel {self.slack_channel_id}")
            else:
                self.logger.error(f"Slack API returned ok=false: {response.get('error', 'Unknown error')}")

        except SlackApiError as e:
            error_msg = e.response.get('error', 'Unknown Slack API error') if hasattr(e, 'response') else str(e)
            self.logger.error(f"Slack API error: {error_msg}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending Slack notification: {e}")
