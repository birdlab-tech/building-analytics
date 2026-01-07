"""
Live BMS API Client - Dan's REST API Integration

Connects to the BMS REST API and fetches real-time data.
This replaces static JSON file loading with live data streaming.
"""

import requests
import urllib3
from datetime import datetime
from typing import Dict, List, Optional
import json

# Disable SSL warnings for self-signed certificates (common in BMS systems)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BMSAPIClient:
    """Client for connecting to BMS REST API"""

    def __init__(self, base_url: str, bearer_token: str, verify_ssl: bool = False):
        """
        Initialize BMS API client

        Args:
            base_url: Base URL of the API (e.g., "https://192.168.11.128/rest")
            bearer_token: Authentication bearer token
            verify_ssl: Whether to verify SSL certificates (False for self-signed certs)
        """
        self.base_url = base_url
        self.bearer_token = bearer_token
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer_token}"
        })

    def fetch_current_data(self, timeout: int = 30) -> Dict:
        """
        Fetch current BMS data from the API

        Args:
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing the API response

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        try:
            response = self.session.get(
                self.base_url,
                verify=self.verify_ssl,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.SSLError as e:
            print(f"SSL Error: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error: {e}")
            raise
        except requests.exceptions.Timeout as e:
            print(f"Request timed out after {timeout}s: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error {response.status_code}: {response.text}")
            raise

    def parse_response(self, raw_data: Dict) -> List[Dict]:
        """
        Parse BMS API response into standardized format

        Converts from API format:
        {
            "points": [
                {"/rest/L11OS11D1_ChW Sec Pump1 Speed": {
                    "value": 72.09,
                    "last_update_time": "Wed Jan 7 14:45:53 2026 UTC"
                }}
            ]
        }

        To standardized format matching your existing JSON:
        [
            {
                "ObjectId": "generated-hash",
                "InstallationId": "from-config",
                "At": "2026-01-07T14:45:53.000Z",
                "Value": "72.09",
                "Label": "L11_OS11_D1_ChW Sec Pump1 Speed"
            }
        ]

        Args:
            raw_data: Raw API response dictionary

        Returns:
            List of standardized data point dictionaries
        """
        parsed_points = []

        for point in raw_data.get("points", []):
            for path, details in point.items():
                # Extract point name from path (remove "/rest/" prefix)
                point_name = path.replace("/rest/", "")

                # Normalize label format (OS -> O, add underscores)
                # L11OS11D1 -> L11_O11_D1
                label = self._normalize_label(point_name)

                # Parse timestamp
                timestamp = self._parse_timestamp(details.get("last_update_time"))

                # Generate ObjectId (hash of label for consistency)
                object_id = self._generate_object_id(label)

                parsed_points.append({
                    "ObjectId": object_id,
                    "InstallationId": "dan-bms-live",  # Configurable
                    "At": timestamp,
                    "Value": str(details.get("value")),  # Convert to string for consistency
                    "Label": label
                })

        return parsed_points

    def _normalize_label(self, label: str) -> str:
        """
        Normalize label format to match existing convention

        Converts: L11OS11D1_ChW Sec Pump1 Speed
        To:       L11_O11_D1_ChW Sec Pump1 Speed
        """
        # Split into prefix and description
        parts = label.split("_", 1)
        if len(parts) != 2:
            return label  # Return as-is if format doesn't match

        prefix, description = parts

        # Parse prefix: L11OS11D1 -> L11_O11_D1
        import re
        match = re.match(r'L(\d+)OS(\d+)([A-Z])(\d+)', prefix)

        if match:
            line, outstation, point_type, point_num = match.groups()
            normalized_prefix = f"L{line}_O{outstation}_{point_type}{point_num}"
            return f"{normalized_prefix}_{description}"

        return label  # Return as-is if parsing fails

    def _parse_timestamp(self, timestamp_str: str) -> str:
        """
        Parse timestamp string to ISO 8601 format

        Converts: "Wed Jan  7 14:45:53 2026 UTC"
        To:       "2026-01-07T14:45:53.000Z"
        """
        # If timestamp is empty or None, use current time silently
        if not timestamp_str or timestamp_str.strip() == "":
            return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

        try:
            # Parse the timestamp
            dt = datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y %Z")

            # Convert to ISO 8601
            return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        except Exception as e:
            # Only print warning for non-empty timestamps that fail to parse
            print(f"Warning: Could not parse timestamp '{timestamp_str}': {e}")
            # Fallback to current time
            return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _generate_object_id(self, label: str) -> str:
        """Generate consistent ObjectId from label using MD5 hash"""
        import hashlib
        return hashlib.md5(label.encode()).hexdigest()

    def fetch_and_parse(self) -> List[Dict]:
        """
        Convenience method to fetch and parse in one call

        Returns:
            List of parsed data points
        """
        raw_data = self.fetch_current_data()
        return self.parse_response(raw_data)

    def save_to_json(self, filename: str = "live_data_snapshot.json"):
        """
        Fetch current data and save to JSON file

        Args:
            filename: Output filename
        """
        data = self.fetch_and_parse()

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"[OK] Saved {len(data)} points to {filename}")
        return data


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Configuration
    API_URL = "https://192.168.11.128/rest"
    BEARER_TOKEN = "6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji"

    # Create client
    print("Connecting to BMS API...")
    client = BMSAPIClient(API_URL, BEARER_TOKEN)

    # Fetch and parse data
    print("Fetching current data...")
    data = client.fetch_and_parse()

    print(f"\n[OK] Retrieved {len(data)} data points")
    print("\nSample points:")
    for i, point in enumerate(data[:5]):
        print(f"  {i+1}. {point['Label']}: {point['Value']}")

    # Save to JSON file
    print("\nSaving to JSON file...")
    client.save_to_json("live_data_snapshot.json")

    print("\n[OK] Done! You can now use this data with your existing visualization scripts.")
    print("     Try running: python quick_viz_example.py")
    print("                  (update it to load 'live_data_snapshot.json' instead)")
