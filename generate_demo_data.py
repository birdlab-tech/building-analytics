"""Generate demo BMS data for testing"""
from influxdb_client import InfluxDBClient, Point
from datetime import datetime, timedelta
import random

INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "bms-super-secret-token-change-in-production"
INFLUXDB_ORG = "birdlab"
INFLUXDB_BUCKET = "bms_data"

SENSORS = [
    ("ChW Sec Pump1 Speed", 50, 100),
    ("ChW Sec Pump2 Speed", 30, 80),
    ("LPHW Sec Pump1 Speed", 40, 90),
    ("AHU1 Supply Air Temp", 18, 24),
    ("Outside Temperature", 5, 15),
    ("Boiler Flow Temp", 60, 80),
]

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api()

print("Generating 48 hours of demo data...")
start_time = datetime.utcnow() - timedelta(hours=48)

for i in range(576):
    timestamp = start_time + timedelta(minutes=i * 5)
    for sensor_name, min_val, max_val in SENSORS:
        value = (min_val + max_val) / 2 + random.uniform(-10, 10)
        point = Point("bms_data") \
            .tag("tenant_id", "sackville") \
            .tag("building_id", "sackville_hq") \
            .tag("sensor_name", sensor_name) \
            .field("value", round(value, 2)) \
            .time(timestamp)
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    if (i + 1) % 100 == 0:
        print(f"Progress: {i + 1}/576")

print("✅ Demo data complete!")
client.close()
