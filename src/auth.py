import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict

import requests


@dataclass
class SessionCookies:
    """Container for easydoct.com session cookies."""
    session_key: str
    user_session_key: str
    aspnet_cookies: str

    def is_valid(self) -> bool:
        """Check if all cookies are present."""
        return bool(self.session_key and self.user_session_key and self.aspnet_cookies)


class EasydoctAuthenticator:
    """Handle automated login and session cookie retrieval for easydoct.com using API calls."""

    LOGIN_URL = "https://www.easydoct.com/EdPatient/EdPatientSignin"

    def __init__(self):
        """Initialize authenticator."""
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

    def _extract_viewstate_fields(self, html: str) -> Optional[Dict[str, str]]:
        """
        Extract ASP.NET ViewState fields from HTML.

        Args:
            html: HTML content of the login page

        Returns:
            Dictionary with ViewState fields or None if extraction failed
        """
        try:
            viewstate_match = re.search(r'id="__VIEWSTATE"\s+value="([^"]+)"', html)
            viewstate_gen_match = re.search(r'id="__VIEWSTATEGENERATOR"\s+value="([^"]+)"', html)
            event_val_match = re.search(r'id="__EVENTVALIDATION"\s+value="([^"]+)"', html)

            if not all([viewstate_match, viewstate_gen_match, event_val_match]):
                self.logger.error("Could not extract all required ASP.NET ViewState fields")
                return None

            fields = {
                '__VIEWSTATE': viewstate_match.group(1),
                '__VIEWSTATEGENERATOR': viewstate_gen_match.group(1),
                '__EVENTVALIDATION': event_val_match.group(1)
            }

            self.logger.debug(f"Extracted ViewState fields: "
                              f"VIEWSTATE={len(fields['__VIEWSTATE'])} chars, "
                              f"GENERATOR={fields['__VIEWSTATEGENERATOR']}, "
                              f"EVENTVALIDATION={len(fields['__EVENTVALIDATION'])} chars")

            return fields

        except Exception as e:
            self.logger.error(f"Error extracting ViewState fields: {e}")
            return None

    def _build_headers(self, referer: str) -> Dict[str, str]:
        """
        Build HTTP headers that mimic a real browser.

        Args:
            referer: Referer URL for the request

        Returns:
            Dictionary of HTTP headers
        """
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.easydoct.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': referer,
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        }

    def login(self, email: str, password: str, exam_url: str) -> Optional[SessionCookies]:
        """
        Perform automated login and retrieve session cookies using API calls.

        Args:
            email: User email for easydoct.com
            password: User password
            exam_url: Direct URL to the exam booking page

        Returns:
            SessionCookies object if successful, None otherwise
        """
        try:
            self.logger.info("Starting API-based login process...")

            # Step 1: GET login page to extract ViewState
            self.logger.debug(f"Fetching login page: {self.LOGIN_URL}")

            response = self.session.get(
                self.LOGIN_URL,
                headers=self._build_headers(exam_url),
                timeout=30
            )

            if response.status_code != 200:
                self.logger.error(f"Failed to load login page: HTTP {response.status_code}")
                return None

            self.logger.debug("Login page loaded successfully")

            # Step 2: Extract ViewState fields
            viewstate_fields = self._extract_viewstate_fields(response.text)
            if not viewstate_fields:
                return None

            # Step 3: Prepare login form data
            login_data = {
                **viewstate_fields,
                'ctl00$ContentPlaceHolder1$inputEmail': email,
                'ctl00$ContentPlaceHolder1$edPatientSigninInputPassword': password,
                'ctl00$ContentPlaceHolder1$ButtonLogin': 'Connexion'
            }

            self.logger.debug("Submitting login form...")

            # Step 4: POST login request
            response = self.session.post(
                self.LOGIN_URL,
                data=login_data,
                headers=self._build_headers(self.LOGIN_URL),
                timeout=30,
                allow_redirects=True
            )

            if response.status_code not in (200, 302):
                self.logger.error(f"Login request failed: HTTP {response.status_code}")
                return None

            self.logger.debug(f"Login response: HTTP {response.status_code}")

            # Step 5: Navigate to exam page to ensure cookies are set in correct context
            self.logger.debug(f"Navigating to exam page: {exam_url}")

            response = self.session.get(
                exam_url,
                headers=self._build_headers(self.LOGIN_URL),
                timeout=30
            )

            # Step 6: Verify login and extract cookies
            if self._is_logged_in():
                self.logger.info("Login successful!")
                return self._extract_cookies()
            else:
                self.logger.error("Login appears to have failed - could not verify successful login")
                return None

        except requests.exceptions.Timeout as e:
            self.logger.error(f"Timeout during login process: {e}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error during login: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during login process: {e}")
            return None

    def _is_logged_in(self) -> bool:
        """
        Check if user is logged in by looking for session cookies.

        Returns:
            True if logged in, False otherwise
        """
        cookies = self.session.cookies
        cookie_names = {cookie.name for cookie in cookies}

        # Check for presence of session cookies
        has_session = 'SessionKey' in cookie_names
        has_aspnet = '.AspNet.Cookies' in cookie_names

        self.logger.debug(f"Cookie check: SessionKey={has_session}, AspNet.Cookies={has_aspnet}")

        return has_session and has_aspnet

    def _extract_cookies(self) -> Optional[SessionCookies]:
        """
        Extract session cookies from the session.

        Returns:
            SessionCookies object if all cookies found, None otherwise
        """
        try:
            cookies = self.session.cookies
            cookie_dict = {cookie.name: cookie.value for cookie in cookies}

            session_key = cookie_dict.get('SessionKey', '')
            user_session_key = cookie_dict.get('UserSessionKey', 'N')
            aspnet_cookies = cookie_dict.get('.AspNet.Cookies', '')

            session_cookies = SessionCookies(
                session_key=session_key,
                user_session_key=user_session_key,
                aspnet_cookies=aspnet_cookies
            )

            if session_cookies.is_valid():
                self.logger.info("Successfully extracted session cookies")
                self.logger.debug(f"SessionKey: {session_key[:20]}...")
                self.logger.debug(f"UserSessionKey: {user_session_key}")
                self.logger.debug(f"AspNet.Cookies: {aspnet_cookies[:30]}...")
                return session_cookies
            else:
                self.logger.error("Could not find all required session cookies")
                return None

        except Exception as e:
            self.logger.error(f"Error extracting cookies: {e}")
            return None


def get_session_cookies(
        email: str,
        password: str,
        exam_url: str,
) -> Optional[SessionCookies]:
    """
    Convenience function to get session cookies via automated API-based login.

    Args:
        email: User email for easydoct.com
        password: User password
        exam_url: Direct URL to the exam booking page

    Returns:
        SessionCookies object if successful, None otherwise
    """
    authenticator = EasydoctAuthenticator()
    return authenticator.login(email, password, exam_url)
