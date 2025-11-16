import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv

from notifications import NotificationService


@dataclass
class Config:
    """Configuration for IRM appointment slot checker."""
    # API Configuration
    api_url: str
    session_key: str
    user_session_key: str
    aspnet_cookies: str

    # Appointment Parameters
    exam_type_id: str
    exam_id: str
    patient_birth_date: str

    # Polling Configuration
    poll_interval: int

    # Logging Configuration
    log_level: str
    log_file: str

    # Notification Configuration
    notifications_enabled: bool
    slack_token: Optional[str] = None
    slack_channel_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        load_dotenv()

        # Required fields
        required_fields = {
            'API_URL': 'api_url',
            'SESSION_KEY': 'session_key',
            'USER_SESSION_KEY': 'user_session_key',
            'ASPNET_COOKIES': 'aspnet_cookies',
            'EXAM_TYPE_ID': 'exam_type_id',
            'EXAM_ID': 'exam_id',
            'PATIENT_BIRTH_DATE': 'patient_birth_date',
        }

        config_dict: Dict[str, Any] = {}
        missing_fields: List[str] = []

        for env_var, field_name in required_fields.items():
            value = os.getenv(env_var)
            if not value:
                missing_fields.append(env_var)
            config_dict[field_name] = value

        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")

        # Optional fields with defaults
        config_dict['poll_interval'] = int(os.getenv('POLL_INTERVAL_SECONDS', '60'))
        config_dict['log_level'] = os.getenv('LOG_LEVEL', 'INFO')
        config_dict['log_file'] = os.getenv('LOG_FILE', 'irm_slots.log')

        # Notification configuration
        config_dict['notifications_enabled'] = os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        config_dict['slack_token'] = os.getenv('SLACK_TOKEN')
        config_dict['slack_channel_id'] = os.getenv('SLACK_CHANNEL_ID')

        return cls(**config_dict)

    def get_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        return {
            "Host": "www.easydoct.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.easydoct.com",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://www.easydoct.com/rdv/gie-irldr-imagerie-rennes",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "Cookie": (
                f"SessionKey={self.session_key}; "
                f"UserSessionKey={self.user_session_key}; "
                f".AspNet.Cookies={self.aspnet_cookies}"
            )
        }

    def get_payload(self) -> Dict[str, Any]:
        """Build request payload."""
        return {
            "examTypeId": self.exam_type_id,
            "minDate": datetime.today().strftime("%Y%m%d"),
            "examId": self.exam_id,
            "examSetId": None,
            "practitionerId": None,
            "officePlaceIds": None,
            "isMobileView": None,
            "patientBirthDate": self.patient_birth_date,
            "officePlaceHubId": None
        }


class IRMSlotChecker:
    """Main application for checking IRM appointment availability."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.notification_service = NotificationService(
            slack_token=config.slack_token,
            slack_channel_id=config.slack_channel_id,
            enabled=config.notifications_enabled
        )

    def check_availability(self) -> bool:
        """Check for available appointment slots."""
        try:
            response = requests.post(
                self.config.api_url,
                headers=self.config.get_headers(),
                json=self.config.get_payload(),
                timeout=30
            )

            if response.status_code != 200:
                self.logger.error(f"HTTP error {response.status_code}")
                return False

            data = response.json()
            availability_count = data.get("availabilityCount", 0)

            if availability_count > 0:
                self.logger.info(f"Appointments are available! Count: {availability_count}")

                availability_lines = data.get("availabilityLines", [])
                for line in availability_lines:
                    self.logger.info(f" - {line}")

                # Send notification
                message = f"Found {availability_count} available appointment slot(s)!"
                self.notification_service.send(message, data)

                return True
            else:
                self.logger.info("No slots available")
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False

    def run(self) -> None:
        """Main loop to continuously check for availability."""
        self.logger.info("Starting IRM slot checker...")
        self.logger.info(f"Checking every {self.config.poll_interval} seconds")

        try:
            while True:
                if self.check_availability():
                    self.logger.info("Appointment found! Stopping checker.")
                    break

                time.sleep(self.config.poll_interval)

        except KeyboardInterrupt:
            self.logger.info("Checker stopped by user")
        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}")
            raise


def setup_logging(config: Config) -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor IRM appointment slots on easydoct.com and send Slack notifications.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python IRMslots.py              # Run with default settings from .env
  python IRMslots.py --debug      # Run with debug logging enabled
  python IRMslots.py -d           # Same as --debug (short form)
        """
    )

    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug mode with verbose logging (overrides LOG_LEVEL from .env)'
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    try:
        # Parse command-line arguments
        args = parse_args()

        # Load configuration
        config = Config.from_env()

        # Override log level if debug mode is enabled
        if args.debug:
            config.log_level = 'DEBUG'
            print("Debug mode enabled - verbose logging activated")

        # Setup logging
        setup_logging(config)

        # Create and run checker
        checker = IRMSlotChecker(config)
        checker.run()

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        print("Please check your .env file and ensure all required variables are set.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
