"""
Automatic resolution of exam IDs and location IDs from user-friendly names.
"""
import logging
from typing import Optional, Dict, List, Any

import requests


logger = logging.getLogger(__name__)


class ExamResolver:
    """Resolve exam IDs and location IDs from names."""

    BASE_URL = "https://www.easydoct.com/api/rdv"

    @staticmethod
    def get_exam_id(exam_type_id: str, exam_name: str) -> Optional[str]:
        """
        Get exam ID by searching for exam name.

        Args:
            exam_type_id: The exam type ID (e.g., "3374")
            exam_name: Name or partial name to search for (e.g., "IRM pied")

        Returns:
            Exam ID as string if found, None otherwise
        """
        try:
            logger.info(f"Resolving exam ID for: '{exam_name}'")
            url = f"{ExamResolver.BASE_URL}/getExamType/{exam_type_id}"

            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch exam types: HTTP {response.status_code}")
                return None

            data = response.json()
            exams = data.get('exams', [])

            if not exams:
                logger.error("No exams found in response")
                return None

            # Search for exact match first
            exam_name_lower = exam_name.lower().strip()
            for exam in exams:
                if exam['name'].lower().strip() == exam_name_lower:
                    exam_id = str(exam['id'])
                    logger.info(f"✓ Found exact match: ID {exam_id} - {exam['name']}")
                    return exam_id

            # Search for partial match
            matches = []
            for exam in exams:
                if exam_name_lower in exam['name'].lower():
                    matches.append(exam)

            if len(matches) == 0:
                logger.error(f"No exams found matching '{exam_name}'")
                logger.info("Available exams:")
                for exam in exams[:10]:
                    logger.info(f"  - {exam['name']}")
                return None

            if len(matches) > 1:
                logger.warning(f"Multiple exams match '{exam_name}':")
                for exam in matches:
                    logger.warning(f"  - ID {exam['id']}: {exam['name']}")
                logger.warning("Using first match. Specify more precise name to avoid ambiguity.")

            exam_id = str(matches[0]['id'])
            logger.info(f"✓ Found match: ID {exam_id} - {matches[0]['name']}")
            return exam_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching exams: {e}")
            return None
        except Exception as e:
            logger.error(f"Error resolving exam ID: {e}")
            return None

    @staticmethod
    def get_location_id(
        exam_type_id: str,
        exam_id: str,
        location_name: str
    ) -> Optional[str]:
        """
        Get location (office place) ID by searching for location name.

        Args:
            exam_type_id: The exam type ID (e.g., "3374")
            exam_id: The exam ID (e.g., "56796")
            location_name: Name or partial name to search for (e.g., "CANOPIA")

        Returns:
            Location ID as string if found, None otherwise
        """
        try:
            logger.info(f"Resolving location ID for: '{location_name}'")
            url = (f"{ExamResolver.BASE_URL}/getOfficePlaces/"
                   f"{exam_type_id}/{exam_id}/null/null/null?officePlaceHubId=")

            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch locations: HTTP {response.status_code}")
                return None

            locations = response.json()

            if not isinstance(locations, list):
                logger.error("Unexpected response format for locations")
                return None

            if not locations:
                logger.error("No locations found in response")
                return None

            # Search for exact match first
            location_name_lower = location_name.lower().strip()
            for location in locations:
                loc_name = location.get('name', '').lower().strip()
                if loc_name == location_name_lower:
                    loc_id = str(location['id'])
                    logger.info(f"✓ Found exact match: ID {loc_id} - {location['name']}")
                    return loc_id

            # Search for partial match
            matches = []
            for location in locations:
                loc_name = location.get('name', '')
                if location_name_lower in loc_name.lower():
                    matches.append(location)

            if len(matches) == 0:
                logger.error(f"No locations found matching '{location_name}'")
                logger.info("Available locations:")
                for location in locations:
                    logger.info(f"  - {location.get('name')}")
                return None

            if len(matches) > 1:
                logger.warning(f"Multiple locations match '{location_name}':")
                for location in matches:
                    logger.warning(f"  - ID {location['id']}: {location.get('name')}")
                logger.warning("Using first match. Specify more precise name to avoid ambiguity.")

            loc_id = str(matches[0]['id'])
            logger.info(f"✓ Found match: ID {loc_id} - {matches[0]['name']}")
            return loc_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while fetching locations: {e}")
            return None
        except Exception as e:
            logger.error(f"Error resolving location ID: {e}")
            return None

    @staticmethod
    def list_available_exams(exam_type_id: str) -> List[Dict[str, Any]]:
        """
        List all available exams for debugging/reference.

        Args:
            exam_type_id: The exam type ID (e.g., "3374")

        Returns:
            List of exam dictionaries with 'id' and 'name' keys
        """
        try:
            url = f"{ExamResolver.BASE_URL}/getExamType/{exam_type_id}"
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                return []

            data = response.json()
            return data.get('exams', [])

        except Exception as e:
            logger.error(f"Error listing exams: {e}")
            return []

    @staticmethod
    def list_available_locations(exam_type_id: str, exam_id: str) -> List[Dict[str, Any]]:
        """
        List all available locations for debugging/reference.

        Args:
            exam_type_id: The exam type ID (e.g., "3374")
            exam_id: The exam ID (e.g., "56796")

        Returns:
            List of location dictionaries
        """
        try:
            url = (f"{ExamResolver.BASE_URL}/getOfficePlaces/"
                   f"{exam_type_id}/{exam_id}/null/null/null?officePlaceHubId=")
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                return []

            return response.json() if isinstance(response.json(), list) else []

        except Exception as e:
            logger.error(f"Error listing locations: {e}")
            return []
