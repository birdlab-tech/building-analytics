"""
Generate Fake Time-Series Data for Demo

Creates realistic BMS temperature data for 3 zones over 1 week:
- 15-minute intervals
- Realistic daily temperature patterns
- Simulates occupied/unoccupied periods
- Perfect for demonstrating Plotly capabilities to Dan
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# =============================================================================
# CONFIGURATION
# =============================================================================

START_DATE = datetime(2026, 1, 1, 0, 0, 0)
DAYS = 7
INTERVAL_MINUTES = 15

# 3 air temperature sensors
SENSORS = [
    {
        'id': 'zone_1_temp',
        'label': 'L11_O11_S1_Zone 1 Air Temperature',
        'base_temp': 21.0,      # Target setpoint
        'amplitude': 3.0,        # Daily swing
        'noise': 0.3,           # Random variation
        'occupied_boost': 2.0   # Extra heat during occupied hours
    },
    {
        'id': 'zone_2_temp',
        'label': 'L11_O11_S2_Zone 2 Air Temperature',
        'base_temp': 22.0,
        'amplitude': 2.5,
        'noise': 0.4,
        'occupied_boost': 1.5
    },
    {
        'id': 'zone_3_temp',
        'label': 'L11_O11_S3_Zone 3 Air Temperature',
        'base_temp': 20.5,
        'amplitude': 3.5,
        'noise': 0.5,
        'occupied_boost': 2.5
    }
]

# Occupied hours (weekdays 7am-6pm)
OCCUPIED_START_HOUR = 7
OCCUPIED_END_HOUR = 18

# =============================================================================
# GENERATE DATA
# =============================================================================

def is_occupied(dt):
    """Check if building is occupied (weekday 7am-6pm)"""
    if dt.weekday() >= 5:  # Weekend
        return False
    return OCCUPIED_START_HOUR <= dt.hour < OCCUPIED_END_HOUR

def generate_temperature(sensor, timestamps):
    """Generate realistic temperature time-series for a sensor"""
    temps = []

    for ts in timestamps:
        # Base temperature with daily cycle
        hours_since_midnight = ts.hour + ts.minute / 60.0
        daily_cycle = sensor['amplitude'] * np.sin(2 * np.pi * (hours_since_midnight - 6) / 24)

        # Occupied boost
        occupied_boost = sensor['occupied_boost'] if is_occupied(ts) else 0

        # Random noise
        noise = np.random.normal(0, sensor['noise'])

        # Combined temperature
        temp = sensor['base_temp'] + daily_cycle + occupied_boost + noise

        temps.append(round(temp, 2))

    return temps

# Generate timestamps
num_intervals = int((DAYS * 24 * 60) / INTERVAL_MINUTES)
timestamps = [START_DATE + timedelta(minutes=i * INTERVAL_MINUTES) for i in range(num_intervals)]

print(f"Generating fake time-series data...")
print(f"  Start: {timestamps[0]}")
print(f"  End: {timestamps[-1]}")
print(f"  Intervals: {len(timestamps)} ({INTERVAL_MINUTES} min intervals)")
print(f"  Sensors: {len(SENSORS)}")

# Generate data for each sensor
all_data = []

for sensor in SENSORS:
    temps = generate_temperature(sensor, timestamps)

    for ts, temp in zip(timestamps, temps):
        all_data.append({
            'ObjectId': sensor['id'],
            'InstallationId': '7c448d21-d839-457f-b773-4f522a2cdbf2',  # Same as real data
            'At': ts.isoformat() + '.000',
            'Value': str(temp),
            'Label': sensor['label']
        })

    print(f"  [OK] Generated {len(temps)} data points for {sensor['label']}")

# =============================================================================
# SAVE DATA
# =============================================================================

output_file = 'fake_timeseries_data.json'

with open(output_file, 'w') as f:
    json.dump(all_data, f, indent=2)

print(f"\n[OK] Saved {len(all_data)} data points to {output_file}")

# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

df = pd.DataFrame(all_data)
df['At'] = pd.to_datetime(df['At'])
df['Value'] = pd.to_numeric(df['Value'])

print("\n" + "="*70)
print("SUMMARY STATISTICS")
print("="*70)

for sensor in SENSORS:
    sensor_data = df[df['ObjectId'] == sensor['id']]
    print(f"\n{sensor['label']}")
    print(f"  Mean: {sensor_data['Value'].mean():.2f}degC")
    print(f"  Min: {sensor_data['Value'].min():.2f}degC")
    print(f"  Max: {sensor_data['Value'].max():.2f}degC")
    print(f"  Std Dev: {sensor_data['Value'].std():.2f}degC")

print("\n" + "="*70)
print("Ready to visualize! Run:")
print("  python visualize_timeseries.py")
print("="*70)
