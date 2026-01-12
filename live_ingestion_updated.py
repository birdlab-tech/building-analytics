"""
Live BMS Data Ingestion - Continuous Polling & Storage
Configured for Sackville BMS and InfluxDB
"""

import time
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import requests
import signal
import sys

# Configuration
BMS_URL = "https://192.168.11.128/rest"
BMS_TOKEN = "6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji"

INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "bms-super-secret-token-change-in-production"
INFLUXDB_ORG = "birdlab"
INFLUXDB_BUCKET = "bms_data"

POLL_INTERVAL = 300  # 5 minutes

running = True

def signal_handler(sig, frame):
    global running
    print("\nShutting down gracefully...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def fetch_bms_data():
    """Fetch data from BMS API"""
    headers = {
        "Authorization": f"Bearer {BMS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(BMS_URL, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching BMS data: {e}")
        return None

def store_in_influxdb(data, write_api):
    """Store BMS data in InfluxDB"""
    if not data or 'points' not in data:
        return 0

    points_written = 0
    timestamp = datetime.utcnow()

    for point_data in data['points']:
        for path, details in point_data.items():
            # Extract point name from path
            point_name = path.replace("/rest/", "")
            value = details.get('value')

            if value is None:
                continue

            try:
                # Create InfluxDB point
                point = Point("bms_data") \
                    .tag("tenant_id", "sackville") \
                    .tag("building_id", "sackville_hq") \
                    .tag("sensor_name", point_name) \
                    .field("value", float(value)) \
                    .time(timestamp)

                write_api.write(bucket=INFLUXDB_BUCKET, record=point)
                points_written += 1
            except Exception as e:
                print(f"Error writing point {point_name}: {e}")

    return points_written

def main():
    print("="*70)
    print("BMS Data Collector - Sackville Building")
    print("="*70)
    print(f"BMS URL: {BMS_URL}")
    print(f"InfluxDB: {INFLUXDB_URL}")
    print(f"Poll interval: {POLL_INTERVAL} seconds")
    print("="*70)

    # Connect to InfluxDB
    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        print("✅ Connected to InfluxDB")
    except Exception as e:
        print(f"❌ Failed to connect to InfluxDB: {e}")
        return 1

    # Main collection loop
    iteration = 0
    while running:
        iteration += 1
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Poll #{iteration}")

        # Fetch data
        data = fetch_bms_data()

        if data:
            # Store in InfluxDB
            points_written = store_in_influxdb(data, write_api)
            print(f"✅ Wrote {points_written} data points to InfluxDB")
        else:
            print("⚠️ No data received from BMS")

        # Wait for next poll
        if running:
            print(f"Sleeping for {POLL_INTERVAL} seconds...")
            time.sleep(POLL_INTERVAL)

    # Cleanup
    client.close()
    print("\n✅ Collector stopped gracefully")
    return 0

if __name__ == "__main__":
    # Disable SSL warnings for self-signed cert
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    sys.exit(main())
