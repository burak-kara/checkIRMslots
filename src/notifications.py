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

    def _send_slack(self, message: str, availability_data: Dict[str, Any]) -> None:
        """
        Send notification to Slack via API.

        Args:
            message: The notification message
            availability_data: Full availability data from API response
        """
        try:
            # Slack has a 3000 character limit per text block
            SLACK_TEXT_LIMIT = 3000

            # Extract availability lines for better formatting
            availability_lines = availability_data.get("availabilityLines", [])
            availability_count = availability_data.get("availabilityCount", 0)

            # Build formatted message - use only text-based blocks to avoid validation issues
            blocks = []

            # First block: header with message (truncate if needed)
            header_text = f":hospital: *IRM Appointment Slots Available!*\n{message}"
            if len(header_text) > SLACK_TEXT_LIMIT:
                # Keep header and truncate message if needed
                header_text = f":hospital: *IRM Appointment Slots Available!*\n{message[:SLACK_TEXT_LIMIT - 40]}"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": header_text
                }
            })

            # Second block: metadata (count and timestamp)
            metadata_text = f"*Slots:* {availability_count} | *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": metadata_text
                }
            })

            # Third block: availability details if present
            if availability_lines:
                # Limit to first 5 slots
                display_lines = availability_lines[:5]
                availability_text = "\n".join([f"• {line}" for line in display_lines])

                # Add indicator if there are more slots
                if len(availability_lines) > 5:
                    availability_text += f"\n_(and {len(availability_lines) - 5} more slots)_"

                # Build slots block text and truncate if needed
                slots_block_text = f"*Available Slots:*\n{availability_text}"
                if len(slots_block_text) > SLACK_TEXT_LIMIT:
                    # If too long, just show count of additional slots
                    slots_block_text = f"*Available Slots:* {availability_count} total slots found"

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": slots_block_text
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
