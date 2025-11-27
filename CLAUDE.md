# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that monitors appointment availability on easydoct.com for medical imaging (IRM/MRI)
appointments. The script polls the easydoct.com API at configurable intervals to check for available appointment slots
and sends Slack notifications when slots are found.

## Architecture

**Four-module application** in `src/` directory with clear separation of concerns:

- **`src/main.py`**: Main application file
    - `Config` class: Dataclass that loads and validates configuration from environment variables (supports both
      auto-login and manual cookie modes)
    - `IRMSlotChecker` class: Main application logic for checking availability with automatic session refresh
    - `setup_logging()` function: Configures logging to both console and file
    - `parse_args()` function: Command-line argument parsing (--debug flag)
    - `main()` function: Entry point with error handling and initial login

- **`src/auth.py`**: Authentication and session management module
    - `SessionCookies` dataclass: Container for session cookies
    - `EasydoctAuthenticator` class: Handles automated API-based login with ASP.NET ViewState extraction
    - `get_session_cookies()` function: Convenience function for automated login

- **`src/notifications.py`**: Notification handling module
    - `NotificationService` class: Handles Slack notifications via API with formatted messages

- **`src/resolver.py`**: Automatic ID resolution module
    - `ExamResolver` class: Resolves exam IDs and location IDs from user-friendly names
    - `get_exam_id()` method: Fetches available exams and matches by name
    - `get_location_id()` method: Fetches available locations and matches by name

**Test Suite** in `tests/` directory (23 total tests):

- **`tests/test_main.py`**: Unit tests for availability checking and notifications
    - `IRMSlotCheckerAvailabilityTests` class: 10 test cases for core functionality
    - Covers appointment detection, notifications, authentication errors, and error handling

- **`tests/test_notifications.py`**: Mock tests for Slack notification formatting
    - `SlackNotificationTests` class: 10 test cases for message structure and edge cases
    - Uses mocks to verify message formatting, block structure, and error handling

- **`tests/test_integration_slack.py`**: Integration tests that send REAL Slack notifications
    - `RealSlackNotificationIntegrationTests` class: 3 test cases
    - **Sends actual messages to your Slack channel** using credentials from `.env`
    - Tests real API response format from easydoct with actual notification delivery

The application flow:

1. Parses command-line arguments (--debug flag)
2. Loads configuration from `.env` file
3. Performs automated login if enabled and cookies not present
4. Sets up logging (both console and file)
5. Makes authenticated POST requests to `https://www.easydoct.com/api/rdv/getRdvDayAvailabilities`
6. Automatically refreshes session on 401/403 errors (if auto-login enabled)
7. Checks the response for `availabilityCount > 0`
8. Sends Slack notification if slots are found
9. Runs in an infinite loop until availability is detected or interrupted

## Setup and Configuration

**1. Install dependencies:**

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Create configuration file:**

```bash
cp .env.example .env
```

**3. Edit `.env` file with your settings:**

Authentication mode (choose one):

- **Auto-login mode** (recommended): Set `AUTO_LOGIN_ENABLED=true`
    - Requires: `EASYDOCT_EMAIL`, `EASYDOCT_PASSWORD`, `EXAM_URL`
    - Cookies are auto-generated and refreshed automatically
- **Manual cookie mode**: Set `AUTO_LOGIN_ENABLED=false`
    - Requires: `SESSION_KEY`, `USER_SESSION_KEY`, `ASPNET_COOKIES`
    - Must manually update cookies when they expire

Always required variables:

- `EXAM_TYPE_ID`, `EXAM_ID`: Specific to the appointment type you're monitoring
- `PATIENT_BIRTH_DATE`: Patient information in ISO format

Optional variables:

- `MIN_DATE`: Minimum date for appointment search in `YYYYMMDD` format (e.g., `20251125`). If not specified, defaults to
  today's date.
- `POLL_INTERVAL_SECONDS`: How often to check in seconds (default: 60)
- `POLL_INTERVAL_JITTER_SECONDS`: Randomization amount for polling intervals in seconds (default: 10). Adds randomness to
  avoid bot detection. The actual interval will be: `POLL_INTERVAL_SECONDS ± POLL_INTERVAL_JITTER_SECONDS` (e.g., 60 ± 10
  means checks happen at random intervals between 50-70 seconds). Set to 0 to disable randomization.
- `LOG_LEVEL`: Logging level (default: INFO)
- `NOTIFICATIONS_ENABLED`: Enable/disable Slack notifications (default: true)
- `SLACK_TOKEN`: Slack Bot User OAuth Token (starts with xoxb-)
- `SLACK_CHANNEL_ID`: Slack channel ID to send notifications to

## Running the Script

**Normal mode:**

```bash
python src/main.py
```

**Debug mode (verbose logging):**

```bash
python src/main.py --debug
# or use short form:
python src/main.py -d
```

**Command-line options:**

- `-d, --debug` - Enable debug mode with verbose logging (overrides LOG_LEVEL from .env)
- `-h, --help` - Show help message with all available options

The script will:

- Load configuration from `.env`
- Start logging to both console and `irm_slots.log` file
- Check for availability every N seconds
- Send Slack notifications when slots are found
- Continue monitoring for additional availability until interrupted with Ctrl+C

**Debug mode** is useful during development to see detailed information about:

- API request/response details
- Configuration loading process
- Internal state changes
- Detailed error traces

## Running Tests

The project includes **23 comprehensive unit and integration tests** across three test files.

**Run all tests:**

```bash
python3 -m unittest discover -s tests -p "test*.py"
```

**Run all tests with verbose output:**

```bash
python3 -m unittest discover -s tests -p "test*.py" -v
```

**Run tests from a specific test file:**

```bash
# Run availability and notification unit tests
python3 -m unittest tests.test_main -v

# Run Slack message mock tests (no actual sending)
python3 -m unittest tests.test_notifications -v

# Run REAL Slack integration tests (requires valid .env credentials!)
python3 -m unittest tests.test_integration_slack -v
```

**Run a specific test class:**

```bash
python3 -m unittest tests.test_main.IRMSlotCheckerAvailabilityTests
python3 -m unittest tests.test_notifications.SlackNotificationTests
python3 -m unittest tests.test_integration_slack.RealSlackNotificationIntegrationTests
```

**Run a specific test:**

```bash
python3 -m unittest tests.test_main.IRMSlotCheckerAvailabilityTests.test_returns_true_and_sends_notification_when_slots_available
python3 -m unittest tests.test_notifications.SlackNotificationTests.test_sends_slack_notification_when_slots_found
python3 -m unittest tests.test_integration_slack.RealSlackNotificationIntegrationTests.test_send_real_slack_notification_with_api_response_format
```

**Test Structure:**

**`tests/test_main.py` - IRMSlotCheckerAvailabilityTests (10 tests):**

- **Appointment Detection & Notifications**:
    - Finding available slots and sending Slack notifications
    - Handling API responses with `availabilityCount` and `appointments` array formats
    - Multiple appointment slots with correct count formatting

- **Authentication & Session Management**:
    - Automatic session refresh on 401/403 authentication errors
    - Auto-login retry with new cookies after auth failure
    - Proper header construction with updated session cookies

- **Notification Behavior**:
    - Skipping notifications when no slots available
    - Respecting `NOTIFICATIONS_ENABLED=false` flag
    - NotificationService initialization with correct Slack credentials
    - Proper message formatting with accurate slot counts

- **Error Handling**:
    - Network request exceptions handling
    - HTTP 403 (Forbidden) error handling
    - Graceful failure without sending notifications on errors

**`tests/test_notifications.py` - SlackNotificationTests (10 tests):**

- **Slack Message Formatting**:
    - Sends properly formatted Slack messages with blocks (header, message, fields, slots)
    - Includes correct slot counts and timestamps
    - Truncates slot lists at 5 items with "...and X more" indicator

- **Slack API Integration**:
    - Calls Slack WebClient `chat_postMessage` with correct parameters
    - Verifies channel ID and fallback text
    - Builds complete block structure with all details

- **Configuration Validation**:
    - Skips sending if Slack token is missing
    - Skips sending if channel ID is missing
    - Does not initialize WebClient if no token provided

- **Error Handling**:
    - Catches and logs SlackApiError exceptions
    - Catches and logs unexpected exceptions
    - Handles `ok=false` responses from Slack API

**`tests/test_integration_slack.py` - RealSlackNotificationIntegrationTests (3 tests):**

- **Real Slack Notification Delivery**:
    - Sends actual messages to your configured Slack channel
    - Uses exact API response format from easydoct documentation
    - Loads credentials from `.env` file (SLACK_TOKEN and SLACK_CHANNEL_ID)
    - Verifies complete message delivery workflow

- **Test Scenarios**:
    - Single appointment notification (1 slot)
    - Multiple appointments with truncation (6 slots showing 5 + "...and 1 more")
    - Minimal appointment data (only dayAbbr and startTime)

- **Requirements**:
    - Valid SLACK_TOKEN in `.env` (xoxb-... format)
    - Valid SLACK_CHANNEL_ID in `.env` (C... format)
    - Bot must be added to the Slack channel (invite the app to the channel)
    - Bot must have `chat:write` OAuth scope permission

- **Usage Notes**:
    - These tests ACTUALLY send messages to your Slack channel
    - Tests are skipped if credentials are not configured
    - If you get "not_in_channel" error, add the bot to your Slack channel first
    - Tests verify end-to-end notification workflow with real Slack API

## Debug Utilities

The `src/debug/` directory contains debugging tools for troubleshooting authentication issues:

**`src/debug/debug_page.py`** - Page structure inspector (Optional):

```bash
python src/debug/debug_page.py
```

This optional script helps inspect page structure for debugging purposes by:

- Opening easydoct.com pages in Chrome browser (requires Selenium + Chrome)
- Searching for login form elements (email, password, submit button)
- Listing all forms and input fields with their IDs, names, and types
- Saving page source HTML to `src/debug/page_source.html`
- Saving screenshot to `src/debug/page_screenshot.png`
- Displaying current cookies

**Note:** This is purely for manual debugging/inspection. The main application does NOT require Selenium or Chrome - it
uses API-based login.

**When to use:**

- Need to manually inspect page structure changes
- Verifying form field names after site updates
- Visual inspection of page layout
- Analyzing ViewState or cookie behavior

**Output files:**

- `src/debug/page_source.html` - Full HTML source for manual inspection
- `src/debug/page_screenshot.png` - Visual screenshot of the page

These files are automatically ignored by git.

## Slack Notification Setup

To receive Slack notifications when appointments become available:

1. Create a Slack App and Bot:
    - Go to https://api.slack.com/apps
    - Click "Create New App" → "From scratch"
    - Give it a name (e.g., "IRM Slot Checker") and select your workspace
    - Navigate to "OAuth & Permissions" in the sidebar
    - Under "Scopes" → "Bot Token Scopes", add:
        - `chat:write` - To send messages
        - `chat:write.public` - To send to public channels without joining
    - Click "Install to Workspace" at the top of the page
    - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

2. Get your Slack Channel ID:
    - Open Slack and go to the channel where you want notifications
    - Right-click the channel name → "View channel details"
    - Scroll down, the Channel ID is at the bottom (format: C01234567890)
    - Alternatively, right-click the channel → "Copy link" and extract the ID from URL

3. Add credentials to your `.env` file:
   ```
   NOTIFICATIONS_ENABLED=true
   SLACK_TOKEN=xoxb-your-bot-token-here
   SLACK_CHANNEL_ID=C01234567890
   ```

4. To disable notifications, set:
   ```
   NOTIFICATIONS_ENABLED=false
   ```

The Slack message includes:

- Formatted header with emoji
- Number of available slots
- Timestamp
- List of available time slots (up to 5, with count if more)

## Code Structure and Best Practices

**Type Hints**: All functions and class methods include type annotations for better IDE support and type checking.

**Configuration Management**: All sensitive data and configuration is loaded from environment variables, never committed
to git.

**Logging**: Uses Python's `logging` module:

- Console output for real-time monitoring
- File output (`irm_slots.log`) for persistence
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)

**Error Handling**: Comprehensive error handling for:

- Missing or invalid configuration
- Network/API failures
- Notification delivery failures
- Authentication errors with automatic session refresh

**Modular Design**:

- Authentication separated into `auth.py` module
    - API-based login using requests library
    - ASP.NET ViewState extraction for form authentication
    - Automatic cookie extraction and management
    - Lightweight, no browser dependencies
- Notifications separated into `notifications.py` module
    - Slack API integration with formatted messages
    - Easy to extend with additional notification methods
- Clean separation between business logic, authentication, and notifications

**Automated Session Management**:

- Initial login performed automatically if cookies not present
- Automatic re-login on 401/403 authentication errors
- Session cookies updated in Config after successful login
- Prevents manual cookie extraction and maintenance

**Key Classes and Methods**:

- `Config.from_env()` - Load configuration from environment (supports both auth modes)
- `Config.get_headers()` - Build authenticated request headers
- `Config.get_payload()` - Build request payload with current date
- `EasydoctAuthenticator.login()` - Perform automated API-based login with ViewState handling
- `EasydoctAuthenticator._extract_viewstate_fields()` - Extract ASP.NET ViewState fields from HTML
- `EasydoctAuthenticator._extract_cookies()` - Extract session cookies from requests session
- `get_session_cookies()` - Convenience function for automated login
- `NotificationService.send()` - Send Slack notification
- `IRMSlotChecker._perform_auto_login()` - Perform auto-login and update cookies
- `IRMSlotChecker.check_availability()` - Check for slots with auto-refresh on auth errors
- `IRMSlotChecker.run()` - Main polling loop

## Important Notes

- **Automated login**: When `AUTO_LOGIN_ENABLED=true`, the script handles all authentication automatically using API
  calls. No manual cookie extraction needed.
- **Cookie expiration**: With auto-login enabled, cookies are automatically refreshed on expiration. With manual mode,
  you must update cookies when they expire.
- **Sensitive data**: Never commit `.env` file to git. It contains email/password credentials (if using auto-login),
  session cookies, and Slack bot token.
- **API-based authentication**: The login process uses direct HTTP requests with ASP.NET ViewState extraction. Fast,
  lightweight, and no browser dependencies.
- **Logs**: The `irm_slots.log` file will grow over time. Consider rotating or cleaning it periodically.
- **Patient-specific**: Configuration is specific to a particular patient and appointment type. Update `EXAM_TYPE_ID`,
  `EXAM_ID`, and `PATIENT_BIRTH_DATE` as needed.
- **Slack rate limits**: The script sends one Slack notification when slots are found and then stops. No rate limiting
  is needed.
- **Bot detection avoidance**: By default, the polling interval includes randomization (60 ± 10 seconds) to appear less
  like a bot. You can adjust `POLL_INTERVAL_JITTER_SECONDS` to increase/decrease the randomness, or set it to 0 to disable.
  Higher jitter values make the polling pattern less predictable. This helps avoid being rate-limited or blocked by the
  target API.

## Example API Response Structure

The API returns appointment availability in the following nested structure:

```json
{
  "availabilityLines": [
    {
      "appointments": [
        {
          "id": "uuid-string",
          "dayAbbr": "15 janvier",
          "startTime": "14:00",
          "officePlaceName": "Clinic Name - Department",
          "examTypeId": 1234,
          "examTypeName": "MRI Type Name",
          "examId": 5678,
          "examName": "Specific Exam Name"
        },
        null,
        null
      ]
    },
    {
      "appointments": [
        {
          "id": "uuid-string",
          "dayAbbr": "15 janvier",
          "startTime": "14:15",
          "officePlaceName": "Clinic Name - Department",
          "examTypeId": 1234,
          "examTypeName": "MRI Type Name",
          "examId": 5678,
          "examName": "Specific Exam Name"
        },
        null
      ]
    }
  ],
  "availabilityCount": 140
}
```

**Response Fields:**
- `availabilityLines`: Array of time slots, each containing an `appointments` array with schedule details
- `appointments`: Array with appointment objects at available indices and `null` at unavailable indices
- `availabilityCount`: Total number of available appointments
- `dayAbbr`: Formatted date (e.g., "15 janvier")
- `startTime`: Appointment start time (e.g., "14:00")
- `officePlaceName`: Clinical facility name and location
- `examTypeName`: Type of medical examination
- `examName`: Specific exam name
