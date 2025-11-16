# IRM Appointment Slot Checker

A Python application that monitors appointment availability on easydoct.com for medical imaging (IRM/MRI) appointments and sends Slack notifications when slots become available.

## Features

- 🔄 Automated polling of appointment availability
- 🔐 Automated login with session management (no manual cookie extraction!)
- 📱 Slack notifications with formatted messages
- 📊 Configurable polling intervals
- 📝 Detailed logging (console + file)
- 🔧 Secure configuration via environment variables
- ⚡ Type-safe code with full type hints
- 🔄 Automatic session refresh when cookies expire

## Prerequisites

- Python 3.8 or higher
- A Slack workspace with permissions to create apps
- Access to easydoct.com account (email/password)

## Installation

1. **Clone the repository** (or download the files):
   ```bash
   cd checkIRMslots
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Create your configuration file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and configure the following**:

### Authentication Mode

Choose between **automated login** (recommended) or **manual cookie** mode:

**Option 1: Automated Login (Recommended)**

Set `AUTO_LOGIN_ENABLED=true` and configure:
- `EASYDOCT_EMAIL` - Your easydoct.com email
- `EASYDOCT_PASSWORD` - Your easydoct.com password
- `EXAM_URL` - Direct URL to your exam booking page

Benefits:
- ✅ No manual cookie extraction needed
- ✅ Automatic session refresh when cookies expire
- ✅ More reliable for long-running monitoring

**Option 2: Manual Cookies**

Set `AUTO_LOGIN_ENABLED=false` and configure:
- `SESSION_KEY` - Your session key
- `USER_SESSION_KEY` - User session key (usually "N")
- `ASPNET_COOKIES` - ASP.NET authentication cookie

Note: You'll need to manually update cookies when they expire. See "Getting Session Cookies" section below.

### Required Settings (Both Modes)

**Appointment Parameters**:
- `EXAM_TYPE_ID` - The type of medical exam (e.g., "3374")
- `EXAM_ID` - Specific exam identifier (e.g., "56794")
- `PATIENT_BIRTH_DATE` - Patient birth date in ISO format (e.g., "1979-04-18T22:00:00.000+02:00")

### Optional Settings

- `POLL_INTERVAL_SECONDS` - How often to check for slots (default: 60)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `LOG_FILE` - Log file location (default: irm_slots.log)

### Slack Notification Settings

- `NOTIFICATIONS_ENABLED` - Enable/disable notifications (default: true)
- `SLACK_TOKEN` - Your Slack Bot User OAuth Token
- `SLACK_CHANNEL_ID` - Channel ID where notifications will be sent

## Slack Setup

To receive Slack notifications:

1. **Create a Slack App**:
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name it (e.g., "IRM Slot Checker") and select your workspace

2. **Configure Bot Permissions**:
   - Navigate to "OAuth & Permissions"
   - Under "Bot Token Scopes", add:
     - `chat:write` - Send messages
     - `chat:write.public` - Send to public channels without joining
   - Click "Install to Workspace"
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

3. **Get Channel ID**:
   - Right-click on your desired Slack channel
   - Select "View channel details"
   - Copy the Channel ID at the bottom (format: C01234567890)

4. **Update `.env` file**:
   ```
   SLACK_TOKEN=xoxb-your-token-here
   SLACK_CHANNEL_ID=C01234567890
   ```

## Running the Application

**Normal mode:**
```bash
python src/main.py
```

**Debug mode (for development/troubleshooting):**
```bash
python src/main.py --debug
# or use short form:
python src/main.py -d
```

**Available options:**
- `-d, --debug` - Enable verbose debug logging (overrides LOG_LEVEL from .env)
- `-h, --help` - Display help message and exit

The application will:
- ✅ Load configuration from `.env`
- ✅ Start monitoring for available slots
- ✅ Log activity to console and file
- ✅ Send Slack notification when slots are found
- ✅ Stop automatically after finding availability

To stop the checker manually, press `Ctrl+C`.

**When to use debug mode:**
- Troubleshooting connection issues
- Verifying API requests and responses
- Debugging Slack notification problems
- Understanding configuration loading
- During development

## Getting Session Cookies (Manual Mode Only)

**Note**: If you're using automated login (`AUTO_LOGIN_ENABLED=true`), you can skip this section entirely. The application will handle login and cookie management automatically.

For manual cookie mode (`AUTO_LOGIN_ENABLED=false`):

1. Open your browser and go to easydoct.com
2. Log in and navigate to the appointment booking page
3. Open Developer Tools (F12)
4. Go to Network tab and refresh the page
5. Find a request to easydoct.com
6. Look at the Request Headers
7. Copy the values from the Cookie header:
   - `SessionKey=...`
   - `UserSessionKey=...`
   - `.AspNet.Cookies=...`

**Note**: Session cookies expire periodically. You'll need to update them when the script stops working.

## Logging

Logs are written to:
- **Console**: Real-time monitoring
- **File**: `irm_slots.log` (or as configured in `.env`)

**Log levels:**
- `INFO` (default): Standard operational messages
- `DEBUG` (with --debug flag): Verbose detailed logging for troubleshooting

**Example log output (INFO level):**
```
2025-11-16 14:30:00 - __main__ - INFO - Starting IRM slot checker...
2025-11-16 14:30:00 - __main__ - INFO - Checking every 60 seconds
2025-11-16 14:30:05 - __main__ - INFO - No slots available
2025-11-16 14:31:05 - __main__ - INFO - Appointments are available! Count: 3
2025-11-16 14:31:05 - notifications - INFO - Slack notification sent successfully
```

**Debug mode** shows additional details like:
- Configuration values loaded from .env
- HTTP request/response details
- Slack API interactions
- Internal processing steps

## Troubleshooting

💡 **Tip**: Run with `--debug` flag for detailed logging to help diagnose issues:
```bash
python src/main.py --debug
```

**Configuration errors**:
- Ensure all required variables are set in `.env`
- Check that there are no typos in variable names

**HTTP errors (401, 403)**:
- If using automated login: The script will automatically attempt to re-login
- If using manual cookies: Your session cookies have expired - obtain fresh ones from your browser
- Check your email/password if auto-login repeatedly fails

**Automated login failures**:
- Ensure Chrome/Chromium is installed on your system
- Verify your `EASYDOCT_EMAIL` and `EASYDOCT_PASSWORD` are correct
- Check that `EXAM_URL` points to the correct exam booking page
- Try running with `--debug` to see detailed browser automation logs
- If ChromeDriver issues occur, try: `pip install webdriver-manager`

**Slack notification failures**:
- Verify your bot token is correct
- Ensure the bot has been added to the channel
- Check that the channel ID is correct
- Verify OAuth scopes are configured

**No slots found**:
- Verify `EXAM_TYPE_ID` and `EXAM_ID` are correct
- Check that the API URL hasn't changed
- Review logs for API errors

## Project Structure

```
checkIRMslots/
├── src/
│   ├── main.py          # Main application
│   ├── auth.py          # Automated login handler
│   ├── notifications.py # Slack notification handler
│   └── debug/           # Debug utilities
│       └── debug_page.py # Page structure inspector
├── requirements.txt     # Python dependencies
├── .env.example        # Configuration template
├── .env               # Your configuration (git-ignored)
├── .gitignore         # Git ignore rules
├── README.md          # This file
├── CLAUDE.md          # Developer documentation
└── irm_slots.log      # Log file (created on run)
```

## Security Notes

⚠️ **Never commit your `.env` file to version control!**

The `.env` file contains sensitive information:
- Email/password credentials (if using automated login)
- Session cookies
- Slack bot token
- Personal patient information

These are automatically excluded via `.gitignore`.

## License

Apache License 2.0 - see LICENSE file for details.
