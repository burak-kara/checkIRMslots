# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that monitors appointment availability on easydoct.com for medical imaging (IRM/MRI) appointments. The script polls the easydoct.com API at configurable intervals to check for available appointment slots and sends Slack notifications when slots are found.

## Architecture

**Three-module application** in `src/` directory with clear separation of concerns:

- **`src/main.py`**: Main application file
  - `Config` class: Dataclass that loads and validates configuration from environment variables (supports both auto-login and manual cookie modes)
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
- `POLL_INTERVAL_SECONDS`: How often to check (default: 60)
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
- Stop when appointment is found or interrupted with Ctrl+C

**Debug mode** is useful during development to see detailed information about:
- API request/response details
- Configuration loading process
- Internal state changes
- Detailed error traces

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

**Note:** This is purely for manual debugging/inspection. The main application does NOT require Selenium or Chrome - it uses API-based login.

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

**Configuration Management**: All sensitive data and configuration is loaded from environment variables, never committed to git.

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

- **Automated login**: When `AUTO_LOGIN_ENABLED=true`, the script handles all authentication automatically using API calls. No manual cookie extraction needed.
- **Cookie expiration**: With auto-login enabled, cookies are automatically refreshed on expiration. With manual mode, you must update cookies when they expire.
- **Sensitive data**: Never commit `.env` file to git. It contains email/password credentials (if using auto-login), session cookies, and Slack bot token.
- **API-based authentication**: The login process uses direct HTTP requests with ASP.NET ViewState extraction. Fast, lightweight, and no browser dependencies.
- **Logs**: The `irm_slots.log` file will grow over time. Consider rotating or cleaning it periodically.
- **Patient-specific**: Configuration is specific to a particular patient and appointment type. Update `EXAM_TYPE_ID`, `EXAM_ID`, and `PATIENT_BIRTH_DATE` as needed.
- **Slack rate limits**: The script sends one Slack notification when slots are found and then stops. No rate limiting is needed.
