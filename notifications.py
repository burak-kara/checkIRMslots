import logging
from typing import Dict, Any, Optional
from datetime import datetime

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

    def _send_slack(self, message: str, availability_data: Dict[str, Any]) -> None:
        """
        Send notification to Slack via API.

        Args:
            message: The notification message
            availability_data: Full availability data from API response
        """
        try:
            # Extract availability lines for better formatting
            availability_lines = availability_data.get("availabilityLines", [])
            availability_count = availability_data.get("availabilityCount", 0)

            # Build formatted message with blocks for better Slack presentation
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🏥 IRM Appointment Slots Available!",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{message}*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Slots Found:*\n{availability_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]

            # Add availability details if present
            if availability_lines:
                availability_text = "\n".join([f"• {line}" for line in availability_lines[:5]])
                if len(availability_lines) > 5:
                    availability_text += f"\n_...and {len(availability_lines) - 5} more_"

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Available Slots:*\n{availability_text}"
                    }
                })

            # Send message using Slack API
            response = self.slack_client.chat_postMessage(
                channel=self.slack_channel_id,
                text=message,  # Fallback text for notifications
                blocks=blocks
            )

            if response["ok"]:
                self.logger.info(f"Slack notification sent successfully to channel {self.slack_channel_id}")
            else:
                self.logger.error(f"Slack API returned ok=false: {response}")

        except SlackApiError as e:
            self.logger.error(f"Slack API error: {e.response['error']}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending Slack notification: {e}")
