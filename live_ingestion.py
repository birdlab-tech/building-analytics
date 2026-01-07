"""
Live BMS Data Ingestion - Continuous Polling & Storage

Polls Dan's BMS REST API at regular intervals and stores data in InfluxDB.
This creates a time-series database for historical analysis.
"""

import time
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from live_api_client import BMSAPIClient
import signal
import sys


class LiveBMSIngestion:
    """Continuously poll BMS API and store in InfluxDB"""

    def __init__(
        self,
        bms_url: str,
        bms_token: str,
        influx_url: str = "http://localhost:8086",
        influx_token: str = "your-influx-token",
        influx_org: str = "bms-research",
        influx_bucket: str = "live-bms-data",
        poll_interval: int = 60
    ):
        """
        Initialize live ingestion

        Args:
            bms_url: BMS API URL
            bms_token: BMS Bearer token
            influx_url: InfluxDB URL
            influx_token: InfluxDB authentication token
            influx_org: InfluxDB organization
            influx_bucket: InfluxDB bucket name
            poll_interval: Polling interval in seconds (default: 60s = 1 minute)
        """
        # BMS API client
        self.bms_client = BMSAPIClient(bms_url, bms_token)
        self.poll_interval = poll_interval

        # InfluxDB client
        self.influx_client = InfluxDBClient(
            url=influx_url,
            token=influx_token,
            org=influx_org
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.bucket = influx_bucket
        self.org = influx_org

        # Statistics
        self.total_points_written = 0
        self.poll_count = 0
        self.running = True

        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n\n[INFO] Shutdown signal received. Stopping ingestion...")
        self.running = False

    def categorize_point(self, label: str) -> dict:
        """
        Categorize BMS point for better organization in InfluxDB

        Returns tags for filtering and grouping
        """
        label_lower = label.lower()

        # Determine system type
        if 'boiler' in label_lower:
            system = 'boiler'
        elif 'ahu' in label_lower or 'air' in label_lower:
            system = 'ahu'
        elif 'chw' in label_lower or 'chiller' in label_lower:
            system = 'chiller'
        elif 'lphw' in label_lower:
            system = 'heating'
        elif 'pump' in label_lower:
            system = 'pump'
        elif 'valve' in label_lower:
            system = 'valve'
        elif 'temp' in label_lower:
            system = 'temperature'
        else:
            system = 'other'

        # Determine measurement type
        if 'temp' in label_lower:
            measurement_type = 'temperature'
        elif 'speed' in label_lower:
            measurement_type = 'speed'
        elif 'valve' in label_lower or 'spt' in label_lower:
            measurement_type = 'position'
        elif 'pump' in label_lower:
            measurement_type = 'status'
        elif 'press' in label_lower:
            measurement_type = 'pressure'
        else:
            measurement_type = 'value'

        # Extract location from label (L11_O11 -> Line 11, Outstation 11)
        import re
        match = re.match(r'L(\d+)_O(\d+)_', label)
        if match:
            line, outstation = match.groups()
        else:
            line, outstation = 'unknown', 'unknown'

        return {
            'system': system,
            'measurement_type': measurement_type,
            'line': line,
            'outstation': outstation
        }

    def write_to_influx(self, data_points: list):
        """
        Write data points to InfluxDB

        Args:
            data_points: List of parsed BMS data points
        """
        points = []

        for point in data_points:
            try:
                # Get categorization tags
                tags = self.categorize_point(point['Label'])

                # Convert value to float
                value = float(point['Value'])

                # Create InfluxDB point
                p = Point("bms_point") \
                    .tag("label", point['Label']) \
                    .tag("installation_id", point['InstallationId']) \
                    .tag("object_id", point['ObjectId']) \
                    .tag("system", tags['system']) \
                    .tag("measurement_type", tags['measurement_type']) \
                    .tag("line", tags['line']) \
                    .tag("outstation", tags['outstation']) \
                    .field("value", value) \
                    .time(point['At'])

                points.append(p)

            except (ValueError, TypeError) as e:
                print(f"Warning: Could not write point {point['Label']}: {e}")
                continue

        # Write batch to InfluxDB
        if points:
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            self.total_points_written += len(points)

    def poll_once(self):
        """Perform a single poll and write to database"""
        try:
            # Fetch data from BMS API
            data = self.bms_client.fetch_and_parse()

            # Write to InfluxDB
            self.write_to_influx(data)

            self.poll_count += 1

            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Poll #{self.poll_count}: Wrote {len(data)} points "
                  f"(Total: {self.total_points_written})")

            return len(data)

        except Exception as e:
            print(f"[ERROR] Poll failed: {e}")
            return 0

    def run(self):
        """Run continuous polling loop"""
        print("="*70)
        print("LIVE BMS DATA INGESTION - STARTED")
        print("="*70)
        print(f"BMS API: {self.bms_client.base_url}")
        print(f"InfluxDB: {self.influx_client.url}")
        print(f"Bucket: {self.bucket}")
        print(f"Poll Interval: {self.poll_interval} seconds")
        print(f"Press Ctrl+C to stop gracefully")
        print("="*70)

        # Initial poll
        self.poll_once()

        # Continuous polling
        while self.running:
            try:
                # Wait for next poll
                time.sleep(self.poll_interval)

                # Poll and write
                self.poll_once()

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
                print("Continuing in 10 seconds...")
                time.sleep(10)

        # Cleanup
        print("\n" + "="*70)
        print("SHUTDOWN COMPLETE")
        print("="*70)
        print(f"Total Polls: {self.poll_count}")
        print(f"Total Points Written: {self.total_points_written}")
        print("="*70)

        self.influx_client.close()


# =============================================================================
# CONFIGURATION & MAIN
# =============================================================================

if __name__ == "__main__":
    # BMS API Configuration
    BMS_CONFIG = {
        'url': 'https://192.168.11.128/rest',
        'token': '6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji'
    }

    # InfluxDB Configuration
    # IMPORTANT: Update these values after setting up InfluxDB!
    # Run: docker-compose up -d
    # Then: http://localhost:8086 to get your token
    INFLUX_CONFIG = {
        'url': 'http://localhost:8086',
        'token': 'YOUR_INFLUX_TOKEN_HERE',  # Get from InfluxDB UI
        'org': 'bms-research',
        'bucket': 'live-bms-data'
    }

    # Polling Configuration
    POLL_INTERVAL = 60  # Poll every 60 seconds (1 minute)
    # Adjust based on your needs:
    # - 15 seconds for near-real-time
    # - 60 seconds for standard monitoring
    # - 300 seconds (5 min) for low-frequency logging

    # Check if InfluxDB token is configured
    if INFLUX_CONFIG['token'] == 'YOUR_INFLUX_TOKEN_HERE':
        print("="*70)
        print("ERROR: InfluxDB not configured!")
        print("="*70)
        print("\nPlease follow these steps:")
        print("\n1. Start InfluxDB:")
        print("   docker-compose up -d")
        print("\n2. Open InfluxDB UI:")
        print("   http://localhost:8086")
        print("\n3. Login with:")
        print("   Username: admin")
        print("   Password: password123")
        print("\n4. Go to: Data → API Tokens")
        print("\n5. Copy your token and update INFLUX_CONFIG['token'] in this file")
        print("\n6. Run this script again")
        print("="*70)
        sys.exit(1)

    # Create and run ingestion
    ingestion = LiveBMSIngestion(
        bms_url=BMS_CONFIG['url'],
        bms_token=BMS_CONFIG['token'],
        influx_url=INFLUX_CONFIG['url'],
        influx_token=INFLUX_CONFIG['token'],
        influx_org=INFLUX_CONFIG['org'],
        influx_bucket=INFLUX_CONFIG['bucket'],
        poll_interval=POLL_INTERVAL
    )

    ingestion.run()
