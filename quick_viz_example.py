"""
Quick Visualization Example - No Database Required!

This shows the power of Plotly vs Grafana:
- Run this script directly on your JSON file
- Interactive, publication-ready visualizations
- No infrastructure setup needed

This is what makes your approach better for research.
"""

import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# =============================================================================
# LOAD DATA
# =============================================================================

print("Loading BMS data from JSON...")
with open('2024-07-22T16_25_52.json', 'r') as f:
    data = json.load(f)

# Convert to DataFrame for easy analysis
df = pd.DataFrame(data)
df['At'] = pd.to_datetime(df['At'])
df['Value'] = pd.to_numeric(df['Value'], errors='coerce')

print(f"[OK] Loaded {len(df)} BMS data points")
print(f"   Installation: {df['InstallationId'].iloc[0]}")
print(f"   Timestamp: {df['At'].iloc[0]}")

# =============================================================================
# CATEGORIZE POINTS
# =============================================================================

def categorize_point(label):
    """Simple categorization - your PhD will automate this better"""
    label_lower = label.lower()

    if 'boiler' in label_lower:
        return 'Boiler'
    elif 'ahu' in label_lower or 'air' in label_lower:
        return 'AHU'
    elif 'pump' in label_lower:
        return 'Pump'
    elif 'valve' in label_lower:
        return 'Valve'
    else:
        return 'Other'

df['System'] = df['Label'].apply(categorize_point)

# =============================================================================
# VISUALIZATION 1: System Overview
# =============================================================================

fig1 = px.sunburst(
    df,
    path=['System', 'Label'],
    values='Value',
    title='BMS Point Distribution by System',
    height=600
)

fig1.write_html('01_system_overview.html')
print("\n[OK] Created: 01_system_overview.html")

# =============================================================================
# VISUALIZATION 2: Boiler System Dashboard
# =============================================================================

boiler_df = df[df['System'] == 'Boiler'].copy()

# Find key boiler points
flow_temp = boiler_df[boiler_df['Label'].str.contains('Flow Temp', case=False)]
pumps = boiler_df[boiler_df['Label'].str.contains('Pump', case=False)]
valves = boiler_df[boiler_df['Label'].str.contains('Valve', case=False)]

fig2 = make_subplots(
    rows=3, cols=1,
    subplot_titles=(
        f'Flow Temperatures ({len(flow_temp)} sensors)',
        f'Pump Status ({len(pumps)} pumps)',
        f'Valve Positions ({len(valves)} valves)'
    ),
    vertical_spacing=0.12,
    specs=[[{"type": "bar"}],
           [{"type": "bar"}],
           [{"type": "bar"}]]
)

# Plot 1: Temperatures
if not flow_temp.empty:
    fig2.add_trace(
        go.Bar(
            x=flow_temp['Label'],
            y=flow_temp['Value'],
            name='Temperature',
            marker_color='indianred',
            text=flow_temp['Value'].round(1),
            textposition='outside'
        ),
        row=1, col=1
    )

# Plot 2: Pumps
if not pumps.empty:
    fig2.add_trace(
        go.Bar(
            x=pumps['Label'],
            y=pumps['Value'],
            name='Pump Status',
            marker_color='lightblue',
            text=pumps['Value'].apply(lambda x: 'ON' if x == 1 else 'OFF'),
            textposition='outside'
        ),
        row=2, col=1
    )

# Plot 3: Valves (top 10 only to avoid clutter)
if not valves.empty:
    top_valves = valves.nlargest(10, 'Value')
    fig2.add_trace(
        go.Bar(
            x=top_valves['Label'],
            y=top_valves['Value'],
            name='Valve Position',
            marker_color='lightgreen',
            text=top_valves['Value'].round(1),
            textposition='outside'
        ),
        row=3, col=1
    )

fig2.update_layout(
    height=1000,
    title_text="Boiler System Snapshot",
    showlegend=False
)

fig2.update_yaxes(title_text="degC", row=1, col=1)
fig2.update_yaxes(title_text="Status", row=2, col=1, range=[0, 1.2])
fig2.update_yaxes(title_text="%", row=3, col=1)

# Rotate x-axis labels for readability
fig2.update_xaxes(tickangle=-45)

fig2.write_html('02_boiler_dashboard.html')
print("[OK] Created: 02_boiler_dashboard.html")

# =============================================================================
# VISUALIZATION 3: Temperature Distribution
# =============================================================================

temp_df = df[df['Label'].str.contains('Temp', case=False, na=False)].copy()

# Filter out bad sensors (< -40degC or > 100degC)
temp_df = temp_df[(temp_df['Value'] > -40) & (temp_df['Value'] < 100)]

fig3 = px.histogram(
    temp_df,
    x='Value',
    nbins=30,
    title='Temperature Distribution Across All Sensors',
    labels={'Value': 'Temperature (degC)', 'count': 'Number of Sensors'},
    color_discrete_sequence=['indianred']
)

fig3.add_vline(
    x=temp_df['Value'].mean(),
    line_dash="dash",
    line_color="blue",
    annotation_text=f"Mean: {temp_df['Value'].mean():.1f}degC"
)

fig3.write_html('03_temperature_distribution.html')
print("[OK] Created: 03_temperature_distribution.html")

# =============================================================================
# VISUALIZATION 4: AHU Analysis
# =============================================================================

ahu_df = df[df['System'] == 'AHU'].copy()

# Find heating and cooling valves
htg_valves = ahu_df[ahu_df['Label'].str.contains('Htg Valve', case=False)]
clg_valves = ahu_df[ahu_df['Label'].str.contains('Clg Valve', case=False)]

fig4 = go.Figure()

fig4.add_trace(go.Bar(
    name='Heating Valves',
    x=htg_valves['Label'],
    y=htg_valves['Value'],
    marker_color='red',
    text=htg_valves['Value'].round(1),
    textposition='outside'
))

fig4.add_trace(go.Bar(
    name='Cooling Valves',
    x=clg_valves['Label'],
    y=clg_valves['Value'],
    marker_color='blue',
    text=clg_valves['Value'].round(1),
    textposition='outside'
))

fig4.update_layout(
    title='AHU Heating vs Cooling Valve Positions',
    xaxis_title='AHU Valve',
    yaxis_title='Position (%)',
    barmode='group',
    height=600
)

fig4.update_xaxes(tickangle=-45)

fig4.write_html('04_ahu_analysis.html')
print("[OK] Created: 04_ahu_analysis.html")

# =============================================================================
# ANALYSIS: Detect Inefficiencies
# =============================================================================

print("\n" + "="*70)
print("ANALYSIS: Checking for System Inefficiencies")
print("="*70)

# Check for simultaneous heating and cooling
print("\n1. Simultaneous Heating & Cooling Check:")
for idx, htg_row in htg_valves.iterrows():
    # Try to find matching cooling valve
    ahu_name = htg_row['Label'].split('Htg Valve')[0].strip()

    clg_match = clg_valves[clg_valves['Label'].str.contains(ahu_name, case=False)]

    if not clg_match.empty:
        htg_val = htg_row['Value']
        clg_val = clg_match.iloc[0]['Value']

        if htg_val > 0 and clg_val > 0:
            print(f"   [WARNING] {ahu_name}: Heating={htg_val}%, Cooling={clg_val}%")

# Check for faulty sensors
print("\n2. Faulty Sensor Check (Temperature < -40degC or > 100degC):")
faulty = df[df['Label'].str.contains('Temp', case=False, na=False)]
faulty = faulty[(faulty['Value'] < -40) | (faulty['Value'] > 100)]

if not faulty.empty:
    for _, row in faulty.iterrows():
        print(f"   [WARNING] {row['Label']}: {row['Value']}degC (likely disconnected)")
else:
    print("   [OK] All temperature sensors within normal range")

# Summary statistics
print("\n3. System Summary:")
print(f"   Total BMS Points: {len(df)}")
print(f"   Boiler Points: {len(boiler_df)}")
print(f"   AHU Points: {len(ahu_df)}")
print(f"   Temperature Sensors: {len(temp_df)}")
print(f"   Average Boiler Flow Temp: {flow_temp['Value'].mean():.1f}degC")

print("\n" + "="*70)
print("[OK] DONE! Open the HTML files in your browser to explore.")
print("="*70)
print("\nGenerated Visualizations:")
print("  1. 01_system_overview.html - Sunburst chart of all systems")
print("  2. 02_boiler_dashboard.html - Detailed boiler metrics")
print("  3. 03_temperature_distribution.html - Temperature histogram")
print("  4. 04_ahu_analysis.html - AHU heating vs cooling")
print("\nThese are INTERACTIVE - zoom, pan, hover, export to PNG!")
print("\nWith Claude Code, you can ask me to generate custom analyses")
print("like this on demand. Try asking:")
print('  "Show correlation between outside temp and boiler flow"')
print('  "Find all valves stuck at 0%"')
print('  "Plot energy consumption by system"')
