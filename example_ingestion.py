"""
BMS Data Ingestion Example
Demonstrates how to ingest re:sustain-format JSON into InfluxDB and visualize with Plotly

This is YOUR independent platform - no AWS, no Grafana, full control.
"""

import json
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =============================================================================
# CONFIGURATION
# =============================================================================

INFLUX_CONFIG = {
    'url': 'http://localhost:8086',  # Local InfluxDB instance
    'token': 'your-token-here',      # Generate from InfluxDB UI
    'org': 'building-analytics',
    'bucket': 'bms_data'
}

# =============================================================================
# DATA INGESTION
# =============================================================================

class BMSIngestor:
    """Ingest BMS data from re:sustain JSON format into InfluxDB"""

    def __init__(self, config):
        self.client = InfluxDBClient(**{k: v for k, v in config.items() if k != 'bucket'})
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = config['bucket']
        self.org = config['org']

    def parse_label(self, label):
        """
        Parse BMS label into structured components

        Label format: L{Line}_O{Outstation}_D/S/I/K/W{Number}_{Description}
        Example: L11_O11_S1_Boiler Common Flow Temp

        Returns: dict with structured metadata
        """
        parts = label.split('_', 3)

        if len(parts) < 4:
            return {'line': None, 'outstation': None, 'point_type': None, 'description': label}

        # Extract line number (e.g., "L11" -> 11)
        line = parts[0][1:] if parts[0].startswith('L') else None

        # Extract outstation number (e.g., "O11" -> 11)
        outstation = parts[1][1:] if parts[1].startswith('O') else None

        # Extract point type and number (e.g., "S1" -> type="S", number="1")
        point_code = parts[2]
        point_type_map = {
            'D': 'digital_output',
            'S': 'sensor',
            'I': 'input',
            'K': 'control',
            'W': 'value'
        }
        point_type = point_type_map.get(point_code[0], 'unknown')
        point_number = point_code[1:]

        # Description
        description = parts[3]

        return {
            'line': line,
            'outstation': outstation,
            'point_type': point_type,
            'point_number': point_number,
            'description': description
        }

    def categorize_point(self, label, value):
        """
        Categorize BMS point based on label and value

        This is WHERE YOUR PHD RESEARCH FITS:
        - Categorical identification (boiler, AHU, valve, etc.)
        - Numerical verification (value ranges)
        - Logical relationships (pump linked to boiler)
        """
        label_lower = label.lower()

        # System categorization
        if 'boiler' in label_lower:
            system = 'boiler'
        elif 'ahu' in label_lower or 'air' in label_lower:
            system = 'ahu'
        elif 'valve' in label_lower:
            system = 'valve'
        elif 'pump' in label_lower:
            system = 'pump'
        else:
            system = 'other'

        # Measurement type
        if 'temp' in label_lower:
            measurement = 'temperature'
            unit = '°C'
        elif 'flow' in label_lower and 'temp' not in label_lower:
            measurement = 'flow'
            unit = 'L/s'
        elif 'pressure' in label_lower:
            measurement = 'pressure'
            unit = 'Pa'
        elif 'enable' in label_lower or 'pump' in label_lower:
            measurement = 'status'
            unit = 'binary'
        else:
            measurement = 'control_signal'
            unit = '%'

        return {
            'system': system,
            'measurement': measurement,
            'unit': unit
        }

    def ingest_json_file(self, filepath):
        """Load JSON file and write to InfluxDB"""

        with open(filepath, 'r') as f:
            data = json.load(f)

        points_written = 0

        for item in data:
            # Parse label structure
            label_metadata = self.parse_label(item['Label'])

            # Categorize point
            category_metadata = self.categorize_point(item['Label'], item['Value'])

            # Create InfluxDB point
            point = Point("bms_reading") \
                .tag("installation_id", item['InstallationId']) \
                .tag("object_id", item['ObjectId']) \
                .tag("label", item['Label']) \
                .tag("system", category_metadata['system']) \
                .tag("measurement_type", category_metadata['measurement']) \
                .tag("point_type", label_metadata['point_type']) \
                .tag("line", label_metadata['line'] or 'unknown') \
                .tag("outstation", label_metadata['outstation'] or 'unknown') \
                .field("value", float(item['Value'])) \
                .field("unit", category_metadata['unit']) \
                .time(datetime.fromisoformat(item['At'].replace('.000', '')), WritePrecision.S)

            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            points_written += 1

        print(f"✅ Ingested {points_written} BMS points to InfluxDB")
        return points_written

# =============================================================================
# DATA ANALYSIS & VISUALIZATION
# =============================================================================

class BMSAnalyzer:
    """Analyze and visualize BMS data"""

    def __init__(self, config):
        self.client = InfluxDBClient(**{k: v for k, v in config.items() if k != 'bucket'})
        self.query_api = self.client.query_api()
        self.bucket = config['bucket']
        self.org = config['org']

    def query_system_data(self, installation_id, system, start='-1h'):
        """Query all points for a specific system (e.g., 'boiler', 'ahu')"""

        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start})
            |> filter(fn: (r) => r._measurement == "bms_reading")
            |> filter(fn: (r) => r.installation_id == "{installation_id}")
            |> filter(fn: (r) => r.system == "{system}")
            |> filter(fn: (r) => r._field == "value")
            |> pivot(rowKey:["_time"], columnKey: ["label"], valueColumn: "_value")
        '''

        result = self.query_api.query_data_frame(query, org=self.org)
        return result

    def visualize_boiler_system(self, installation_id):
        """Create interactive Plotly dashboard for boiler system"""

        # Query boiler data
        df = self.query_system_data(installation_id, 'boiler')

        if df.empty:
            print("⚠️ No boiler data found")
            return None

        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            subplot_titles=(
                'Boiler Flow Temperature',
                'Pump Status',
                'Heating Valve Positions'
            ),
            vertical_spacing=0.1
        )

        # Plot 1: Boiler flow temperature
        temp_cols = [col for col in df.columns if 'Flow Temp' in col and 'Boiler' in col]
        for col in temp_cols:
            fig.add_trace(
                go.Scatter(x=df['_time'], y=df[col], name=col, mode='lines'),
                row=1, col=1
            )

        # Plot 2: Pump status
        pump_cols = [col for col in df.columns if 'Pump' in col]
        for col in pump_cols:
            fig.add_trace(
                go.Scatter(x=df['_time'], y=df[col], name=col, mode='lines+markers'),
                row=2, col=1
            )

        # Plot 3: Heating valves
        valve_cols = [col for col in df.columns if 'Valve' in col]
        for col in valve_cols[:5]:  # Limit to first 5 to avoid clutter
            fig.add_trace(
                go.Scatter(x=df['_time'], y=df[col], name=col, mode='lines'),
                row=3, col=1
            )

        # Update layout
        fig.update_layout(
            height=900,
            title_text="Boiler System Performance - Real-Time Monitoring",
            showlegend=True,
            hovermode='x unified'
        )

        fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
        fig.update_yaxes(title_text="Status (On/Off)", row=2, col=1)
        fig.update_yaxes(title_text="Position (%)", row=3, col=1)

        return fig

    def analyze_ahu_efficiency(self, installation_id):
        """
        Analyze AHU efficiency - example of research analysis

        This demonstrates how Claude Code can help generate
        custom analysis code on demand
        """

        df = self.query_system_data(installation_id, 'ahu')

        if df.empty:
            print("⚠️ No AHU data found")
            return None

        # Find heating and cooling valve columns
        htg_valves = [col for col in df.columns if 'Htg Valve' in col]
        clg_valves = [col for col in df.columns if 'Clg Valve' in col]

        # Detect simultaneous heating and cooling (inefficiency)
        inefficiencies = []

        for i, row in df.iterrows():
            for htg, clg in zip(htg_valves, clg_valves):
                if htg in row and clg in row:
                    if row[htg] > 0 and row[clg] > 0:
                        inefficiencies.append({
                            'time': row['_time'],
                            'ahu': htg.replace('Htg Valve', '').strip(),
                            'heating': row[htg],
                            'cooling': row[clg]
                        })

        if inefficiencies:
            print(f"⚠️ Found {len(inefficiencies)} instances of simultaneous heating & cooling")
            return pd.DataFrame(inefficiencies)
        else:
            print("✅ No simultaneous heating/cooling detected")
            return None

# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':

    print("="*70)
    print("BMS DATA INGESTION & ANALYSIS - Independent Platform")
    print("="*70)

    # 1. INGEST DATA
    print("\n1. Ingesting BMS data...")
    ingestor = BMSIngestor(INFLUX_CONFIG)
    ingestor.ingest_json_file('2024-07-22T16_25_52.json')

    # 2. ANALYZE DATA
    print("\n2. Analyzing data...")
    analyzer = BMSAnalyzer(INFLUX_CONFIG)

    installation_id = "7c448d21-d839-457f-b773-4f522a2cdbf2"

    # Check for inefficiencies
    inefficiencies = analyzer.analyze_ahu_efficiency(installation_id)

    # 3. VISUALIZE
    print("\n3. Creating visualization...")
    fig = analyzer.visualize_boiler_system(installation_id)

    if fig:
        fig.write_html('boiler_dashboard.html')
        print("✅ Dashboard saved to: boiler_dashboard.html")
        print("   Open in browser to interact with the visualization")

    print("\n" + "="*70)
    print("DONE! Your independent platform is working.")
    print("="*70)
    print("\nNext steps:")
    print("  1. Set up InfluxDB locally: docker-compose up")
    print("  2. Generate API token in InfluxDB UI")
    print("  3. Run this script to ingest and analyze")
    print("  4. Ask Claude Code to generate new analysis queries!")
