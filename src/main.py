import argparse
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests
from dotenv import load_dotenv

from auth import get_session_cookies
from notifications import NotificationService
from resolver import ExamResolver


@dataclass
class Config:
    """Configuration for IRM appointment slot checker."""
    # API Configuration
    api_url: str
    session_key: Optional[str]
    user_session_key: Optional[str]
    aspnet_cookies: Optional[str]

    # Appointment Parameters
    exam_type_id: str
    exam_id: str
    patient_birth_date: str

    # Polling Configuration
    poll_interval: int
    poll_interval_jitter: int

    # Logging Configuration
    log_level: str
    log_file: str

    # Notification Configuration
    notifications_enabled: bool

    # Optional Fields (with defaults)
    # Appointment Search Parameters
    min_date: Optional[str] = None

    # Auto-resolution Parameters
    exam_name: Optional[str] = None
    location_name: Optional[str] = None
    office_place_ids: Optional[str] = None

    # Notification tokens
    slack_token: Optional[str] = None
    slack_channel_id: Optional[str] = None

    # Automated Login Configuration
    auto_login_enabled: bool = False
    easydoct_email: Optional[str] = None
    easydoct_password: Optional[str] = None
    exam_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        load_dotenv()

        config_dict: Dict[str, Any] = {}

        # Check if auto-login is enabled
        auto_login_enabled = os.getenv('AUTO_LOGIN_ENABLED', 'false').lower() == 'true'
        config_dict['auto_login_enabled'] = auto_login_enabled

        # Always required fields
        always_required = {
            'API_URL': 'api_url',
            'EXAM_TYPE_ID': 'exam_type_id',
            'PATIENT_BIRTH_DATE': 'patient_birth_date',
        }

        # Exam ID can be provided directly or resolved from name
        exam_id = os.getenv('EXAM_ID')
        exam_name = os.getenv('EXAM_NAME')

        if not exam_id and not exam_name:
            raise ValueError("Either EXAM_ID or EXAM_NAME must be provided")

        # Location can be provided directly or resolved from name
        location_name = os.getenv('LOCATION_NAME')
        office_place_ids = os.getenv('OFFICE_PLACE_IDS')

        # Store exam_name and location_name for potential resolution
        config_dict['exam_name'] = exam_name
        config_dict['location_name'] = location_name

        # Conditionally required fields
        if auto_login_enabled:
            # If auto-login is enabled, require login credentials
            required_fields = {
                **always_required,
                'EASYDOCT_EMAIL': 'easydoct_email',
                'EASYDOCT_PASSWORD': 'easydoct_password',
                'EXAM_URL': 'exam_url',
            }
            # Cookies are optional, will be auto-generated
            config_dict['session_key'] = os.getenv('SESSION_KEY')
            config_dict['user_session_key'] = os.getenv('USER_SESSION_KEY')
            config_dict['aspnet_cookies'] = os.getenv('ASPNET_COOKIES')
        else:
            # If auto-login is disabled, require manual cookies
            required_fields = {
                **always_required,
                'SESSION_KEY': 'session_key',
                'USER_SESSION_KEY': 'user_session_key',
                'ASPNET_COOKIES': 'aspnet_cookies',
            }
            # Login credentials are optional
            config_dict['easydoct_email'] = os.getenv('EASYDOCT_EMAIL')
            config_dict['easydoct_password'] = os.getenv('EASYDOCT_PASSWORD')
            config_dict['exam_url'] = os.getenv('EXAM_URL')

        missing_fields: List[str] = []

        for env_var, field_name in required_fields.items():
            value = os.getenv(env_var)
            if not value:
                missing_fields.append(env_var)
            config_dict[field_name] = value

        if missing_fields:
            mode = "auto-login" if auto_login_enabled else "manual cookie"
            raise ValueError(
                f"Missing required environment variables for {mode} mode: {', '.join(missing_fields)}"
            )

        # Optional fields with defaults
        config_dict['poll_interval'] = int(os.getenv('POLL_INTERVAL_SECONDS', '60'))
        config_dict['poll_interval_jitter'] = int(os.getenv('POLL_INTERVAL_JITTER_SECONDS', '10'))
        config_dict['log_level'] = os.getenv('LOG_LEVEL', 'INFO')
        config_dict['log_file'] = os.getenv('LOG_FILE', 'irm_slots.log')
        config_dict['min_date'] = os.getenv('MIN_DATE')

        # Notification configuration
        config_dict['notifications_enabled'] = os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        config_dict['slack_token'] = os.getenv('SLACK_TOKEN')
        config_dict['slack_channel_id'] = os.getenv('SLACK_CHANNEL_ID')

        # Resolve exam ID if needed
        if exam_name and not exam_id:
            logger = logging.getLogger(__name__)
            logger.info(f"Resolving exam ID from name: '{exam_name}'")
            resolved_id = ExamResolver.get_exam_id(config_dict['exam_type_id'], exam_name)
            if not resolved_id:
                raise ValueError(f"Could not resolve exam ID for exam name: '{exam_name}'")
            exam_id = resolved_id
            logger.info(f"Resolved exam ID: {exam_id}")

        config_dict['exam_id'] = exam_id

        # Resolve location ID if needed
        if location_name and not office_place_ids:
            logger = logging.getLogger(__name__)
            logger.info(f"Resolving location ID from name: '{location_name}'")
            resolved_loc = ExamResolver.get_location_id(
                config_dict['exam_type_id'],
                exam_id,
                location_name
            )
            if not resolved_loc:
                raise ValueError(f"Could not resolve location ID for location name: '{location_name}'")
            office_place_ids = resolved_loc
            logger.info(f"Resolved location ID: {office_place_ids}")

        config_dict['office_place_ids'] = office_place_ids

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
        # Use MIN_DATE from env if provided, otherwise use today's date
        min_date = self.min_date if self.min_date else datetime.today().strftime("%Y%m%d")

        return {
            "examTypeId": self.exam_type_id,
            "minDate": min_date,
            "examId": self.exam_id,
            "examSetId": None,
            "practitionerId": None,
            "officePlaceIds": self.office_place_ids,
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
        self._login_attempted = False

    def _perform_auto_login(self) -> bool:
        """
        Perform automated login and update session cookies.

        Returns:
            True if login successful, False otherwise
        """
        if not self.config.auto_login_enabled:
            self.logger.warning("Auto-login is not enabled")
            return False

        if not all([self.config.easydoct_email, self.config.easydoct_password, self.config.exam_url]):
            self.logger.error("Auto-login enabled but credentials are missing")
            return False

        self.logger.info("Attempting automated login...")

        try:
            cookies = get_session_cookies(
                email=self.config.easydoct_email,
                password=self.config.easydoct_password,
                exam_url=self.config.exam_url
            )

            if cookies and cookies.is_valid():
                # Update config with new cookies
                self.config.session_key = cookies.session_key
                self.config.user_session_key = cookies.user_session_key
                self.config.aspnet_cookies = cookies.aspnet_cookies
                self.logger.info("Automated login successful - session cookies updated")
                return True
            else:
                self.logger.error("Automated login failed - could not retrieve valid cookies")
                return False

        except Exception as e:
            self.logger.error(f"Error during automated login: {e}")
            return False

    def check_availability(self) -> bool:
        """Check for available appointment slots."""
        try:
            response = requests.post(
                self.config.api_url,
                headers=self.config.get_headers(),
                json=self.config.get_payload(),
                timeout=30
            )

            # Handle authentication errors
            if response.status_code in (401, 403):
                self.logger.warning(f"Authentication error {response.status_code} - session may have expired")

                # Attempt auto-login if enabled and not already attempted this cycle
                if self.config.auto_login_enabled and not self._login_attempted:
                    self._login_attempted = True
                    if self._perform_auto_login():
                        self.logger.info("Retrying request with new session cookies...")
                        # Retry the request with new cookies
                        response = requests.post(
                            self.config.api_url,
                            headers=self.config.get_headers(),
                            json=self.config.get_payload(),
                            timeout=30
                        )
                        # Reset flag after successful retry
                        if response.status_code == 200:
                            self._login_attempted = False
                    else:
                        self.logger.error("Auto-login failed - cannot continue")
                        return False
                else:
                    self.logger.error("Session expired and auto-login not available")
                    return False

            if response.status_code != 200:
                self.logger.error(f"HTTP error {response.status_code}")
                return False

            data = response.json()
            availability_count = data.get("availabilityCount", 0)
            appointments = data.get("appointments")
            availability_lines = data.get("availabilityLines", [])

            if availability_count == 0 and appointments:
                # Fallback for responses that only include an appointments array
                availability_count = len([
                    appt for appt in appointments
                    if isinstance(appt, dict)
                ])
                if availability_count:
                    data["availabilityCount"] = availability_count

            if not availability_lines and appointments:
                availability_lines = []
                for appt in appointments:
                    if not isinstance(appt, dict):
                        continue
                    day_label = appt.get("dayAbbr") or appt.get("day")
                    time_label = appt.get("startTime") or appt.get("start")
                    if day_label and time_label:
                        availability_lines.append(f"{day_label} {time_label}")
                if availability_lines:
                    data["availabilityLines"] = availability_lines
            else:
                availability_lines = data.get("availabilityLines", [])

            if availability_count > 0:
                self.logger.info(f"Appointments are available! Count: {availability_count}")

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
        base_interval = self.config.poll_interval
        jitter = self.config.poll_interval_jitter

        if jitter > 0:
            self.logger.info(f"Checking every {base_interval} ± {jitter} seconds (random intervals to avoid bot detection)")
        else:
            self.logger.info(f"Checking every {base_interval} seconds")

        try:
            while True:
                if self.check_availability():
                    self.logger.info("Appointment found! Continuing to monitor for additional availability.")

                # Calculate randomized sleep interval
                if jitter > 0:
                    sleep_interval = random.uniform(base_interval - jitter, base_interval + jitter)
                    self.logger.debug(f"Next check in {sleep_interval:.1f} seconds")
                else:
                    sleep_interval = base_interval

                time.sleep(sleep_interval)

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
  python src/main.py              # Run with default settings from .env
  python src/main.py --debug      # Run with debug logging enabled
  python src/main.py -d           # Same as --debug (short form)
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

        # Perform initial login if auto-login is enabled and cookies not valid
        # Check for placeholder values or missing cookies
        has_valid_cookies = (
                config.session_key and
                config.user_session_key and
                config.aspnet_cookies and
                config.session_key != 'your_session_key_here' and
                config.aspnet_cookies != 'your_aspnet_cookies_here'
        )

        if config.auto_login_enabled and not has_valid_cookies:
            logger = logging.getLogger(__name__)
            logger.info("Auto-login enabled and no valid cookies found - performing initial login...")
            checker_temp = IRMSlotChecker(config)
            if not checker_temp._perform_auto_login():
                logger.error("Initial login failed - cannot start checker")
                sys.exit(1)
            # Use the updated config with cookies
            config = checker_temp.config

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
