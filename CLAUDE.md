# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that monitors appointment availability on easydoct.com for medical imaging (IRM/MRI) appointments. The script polls the easydoct.com API at configurable intervals to check for available appointment slots and sends Slack notifications when slots are found.

## Architecture

**Two-file application** with clear separation of concerns:

- **`IRMslots.py`**: Main application file
  - `Config` class: Dataclass that loads and validates configuration from environment variables
  - `IRMSlotChecker` class: Main application logic for checking availability
  - `setup_logging()` function: Configures logging to both console and file
  - `main()` function: Entry point with error handling

- **`notifications.py`**: Notification handling module
  - `NotificationService` class: Handles Slack notifications via webhooks with formatted messages

The application flow:
1. Loads configuration from `.env` file
2. Sets up logging (both console and file)
3. Makes authenticated POST requests to `https://www.easydoct.com/api/rdv/getRdvDayAvailabilities`
4. Checks the response for `availabilityCount > 0`
5. Sends Slack notification if slots are found
6. Runs in an infinite loop until availability is detected or interrupted

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

Required variables:
- `SESSION_KEY`, `USER_SESSION_KEY`, `ASPNET_COOKIES`: Obtain from browser session on easydoct.com
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
python IRMslots.py
```

**Debug mode (verbose logging):**
```bash
python IRMslots.py --debug
# or use short form:
python IRMslots.py -d
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

**Modular Design**:
- Notifications are separated into their own module (`notifications.py`)
- Easy to extend with additional notification methods
- Clean separation between business logic and notification logic

**Key Classes and Methods**:
- `Config.from_env()` - Load configuration from environment
- `Config.get_headers()` - Build authenticated request headers
- `Config.get_payload()` - Build request payload with current date
- `NotificationService.send()` - Send Slack notification
- `IRMSlotChecker.check_availability()` - Check for slots
- `IRMSlotChecker.run()` - Main polling loop

## Important Notes

- **Cookie expiration**: Session cookies in `.env` will expire. When the script reports authentication errors, obtain new cookies from browser and update `.env`.
- **Sensitive data**: Never commit `.env` file to git. It contains session cookies and Slack bot token.
- **Logs**: The `irm_slots.log` file will grow over time. Consider rotating or cleaning it periodically.
- **Patient-specific**: Configuration is specific to a particular patient and appointment type. Update `EXAM_TYPE_ID`, `EXAM_ID`, and `PATIENT_BIRTH_DATE` as needed.
- **Slack rate limits**: The script sends one Slack notification when slots are found and then stops. No rate limiting is needed.
