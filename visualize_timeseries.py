"""
Grafana-Style Time-Series Visualization

Creates interactive line graphs similar to Grafana dashboards.
Perfect for demonstrating to Dan how Plotly > Grafana for research.

Key advantages over Grafana:
- Generated programmatically (no UI clicking)
- Customizable with Claude Code on demand
- Publication-ready exports
- Works with any data source (no database required)
"""

import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# =============================================================================
# LOAD DATA
# =============================================================================

print("Loading fake time-series data...")
with open('fake_timeseries_data.json', 'r') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df['At'] = pd.to_datetime(df['At'])
df['Value'] = pd.to_numeric(df['Value'])

print(f"[OK] Loaded {len(df)} data points")
print(f"   Date range: {df['At'].min()} to {df['At'].max()}")
print(f"   Sensors: {df['Label'].nunique()}")

# =============================================================================
# VISUALIZATION 1: All Sensors - Grafana Style
# =============================================================================

# Get unique sensors
sensors = df['Label'].unique()
colors = ['#FF6B6B', '#4ECDC4', '#FFE66D']  # Red, Teal, Yellow

fig1 = go.Figure()

for i, sensor in enumerate(sensors):
    sensor_data = df[df['Label'] == sensor].sort_values('At')

    fig1.add_trace(go.Scatter(
        x=sensor_data['At'],
        y=sensor_data['Value'],
        name=sensor.split('_')[-1],  # Extract zone name
        mode='lines',
        line=dict(color=colors[i], width=2),
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Time: %{x|%Y-%m-%d %H:%M}<br>' +
                      'Temperature: %{y:.2f}degC<br>' +
                      '<extra></extra>'
    ))

# Grafana-style dark theme
fig1.update_layout(
    title={
        'text': 'Zone Air Temperatures - 7 Day Time-Series',
        'font': {'size': 20, 'color': '#E0E0E0'}
    },
    xaxis=dict(
        title='Time',
        gridcolor='#333333',
        color='#E0E0E0',
        showgrid=True
    ),
    yaxis=dict(
        title='Temperature (degC)',
        gridcolor='#333333',
        color='#E0E0E0',
        showgrid=True
    ),
    plot_bgcolor='#1E1E1E',
    paper_bgcolor='#2D2D2D',
    font=dict(color='#E0E0E0'),
    hovermode='x unified',
    height=600,
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='right',
        x=1,
        bgcolor='rgba(0,0,0,0.5)'
    )
)

fig1.write_html('timeseries_01_all_zones.html')
print("[OK] Created: timeseries_01_all_zones.html")

# =============================================================================
# VISUALIZATION 2: Daily Patterns (Each Zone Separate)
# =============================================================================

fig2 = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    subplot_titles=[s.split('_')[-1] for s in sensors]
)

for i, sensor in enumerate(sensors):
    sensor_data = df[df['Label'] == sensor].sort_values('At')

    fig2.add_trace(
        go.Scatter(
            x=sensor_data['At'],
            y=sensor_data['Value'],
            name=sensor.split('_')[-1],
            mode='lines',
            line=dict(color=colors[i], width=2),
            showlegend=False,
            hovertemplate='Time: %{x|%Y-%m-%d %H:%M}<br>' +
                          'Temperature: %{y:.2f}degC<br>' +
                          '<extra></extra>'
        ),
        row=i+1, col=1
    )

# Grafana-style dark theme
fig2.update_layout(
    title={
        'text': 'Zone Air Temperatures - Individual Panels',
        'font': {'size': 20, 'color': '#E0E0E0'}
    },
    plot_bgcolor='#1E1E1E',
    paper_bgcolor='#2D2D2D',
    font=dict(color='#E0E0E0'),
    hovermode='x unified',
    height=900
)

fig2.update_xaxes(gridcolor='#333333', color='#E0E0E0', showgrid=True)
fig2.update_yaxes(
    title_text='Temp (degC)',
    gridcolor='#333333',
    color='#E0E0E0',
    showgrid=True
)

fig2.write_html('timeseries_02_separate_panels.html')
print("[OK] Created: timeseries_02_separate_panels.html")

# =============================================================================
# VISUALIZATION 3: Weekly Pattern Analysis
# =============================================================================

# Add day of week and hour for pattern analysis
df['DayOfWeek'] = df['At'].dt.day_name()
df['Hour'] = df['At'].dt.hour

# Calculate hourly averages by day
hourly_avg = df.groupby(['Label', 'DayOfWeek', 'Hour'])['Value'].mean().reset_index()

# Order days correctly
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
hourly_avg['DayOfWeek'] = pd.Categorical(hourly_avg['DayOfWeek'], categories=day_order, ordered=True)
hourly_avg = hourly_avg.sort_values('DayOfWeek')

fig3 = go.Figure()

for i, day in enumerate(day_order):
    day_data = hourly_avg[hourly_avg['DayOfWeek'] == day]

    for j, sensor in enumerate(sensors):
        sensor_day_data = day_data[day_data['Label'] == sensor].sort_values('Hour')

        # Show legend only for Monday
        show_legend = (day == 'Monday')

        fig3.add_trace(go.Scatter(
            x=sensor_day_data['Hour'],
            y=sensor_day_data['Value'],
            name=sensor.split('_')[-1] if show_legend else None,
            mode='lines',
            line=dict(color=colors[j], width=2, dash='solid' if day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] else 'dot'),
            legendgroup=sensor,
            showlegend=show_legend,
            hovertemplate=f'<b>{day}</b><br>' +
                          'Hour: %{x}<br>' +
                          'Avg Temp: %{y:.2f}degC<br>' +
                          '<extra></extra>'
        ))

# Grafana-style dark theme
fig3.update_layout(
    title={
        'text': 'Weekly Temperature Patterns (Hourly Averages)',
        'font': {'size': 20, 'color': '#E0E0E0'}
    },
    xaxis=dict(
        title='Hour of Day',
        gridcolor='#333333',
        color='#E0E0E0',
        showgrid=True,
        dtick=2,
        range=[0, 23]
    ),
    yaxis=dict(
        title='Average Temperature (degC)',
        gridcolor='#333333',
        color='#E0E0E0',
        showgrid=True
    ),
    plot_bgcolor='#1E1E1E',
    paper_bgcolor='#2D2D2D',
    font=dict(color='#E0E0E0'),
    hovermode='x unified',
    height=600,
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='right',
        x=1,
        bgcolor='rgba(0,0,0,0.5)'
    ),
    annotations=[
        dict(
            text='Solid lines = Weekdays, Dotted lines = Weekend',
            xref='paper', yref='paper',
            x=0.5, y=-0.15,
            showarrow=False,
            font=dict(color='#999999', size=12)
        )
    ]
)

fig3.write_html('timeseries_03_weekly_patterns.html')
print("[OK] Created: timeseries_03_weekly_patterns.html")

# =============================================================================
# VISUALIZATION 4: Single Day Deep Dive
# =============================================================================

# Take first Monday
monday_data = df[df['DayOfWeek'] == 'Monday'].copy()

fig4 = go.Figure()

for i, sensor in enumerate(sensors):
    sensor_data = monday_data[monday_data['Label'] == sensor].sort_values('At')

    fig4.add_trace(go.Scatter(
        x=sensor_data['At'],
        y=sensor_data['Value'],
        name=sensor.split('_')[-1],
        mode='lines+markers',
        line=dict(color=colors[i], width=2),
        marker=dict(size=4),
        hovertemplate='<b>%{fullData.name}</b><br>' +
                      'Time: %{x|%H:%M}<br>' +
                      'Temperature: %{y:.2f}degC<br>' +
                      '<extra></extra>'
    ))

# Add occupied hours shading
occupied_start = monday_data['At'].min().replace(hour=7, minute=0, second=0)
occupied_end = monday_data['At'].min().replace(hour=18, minute=0, second=0)

fig4.add_vrect(
    x0=occupied_start, x1=occupied_end,
    fillcolor='rgba(255, 230, 109, 0.1)',
    layer='below',
    line_width=0,
    annotation_text='Occupied Hours',
    annotation_position='top left',
    annotation=dict(font=dict(color='#FFE66D', size=12))
)

# Grafana-style dark theme
fig4.update_layout(
    title={
        'text': 'Monday Temperature Profile (15-Minute Resolution)',
        'font': {'size': 20, 'color': '#E0E0E0'}
    },
    xaxis=dict(
        title='Time',
        gridcolor='#333333',
        color='#E0E0E0',
        showgrid=True,
        tickformat='%H:%M'
    ),
    yaxis=dict(
        title='Temperature (degC)',
        gridcolor='#333333',
        color='#E0E0E0',
        showgrid=True
    ),
    plot_bgcolor='#1E1E1E',
    paper_bgcolor='#2D2D2D',
    font=dict(color='#E0E0E0'),
    hovermode='x unified',
    height=600,
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='right',
        x=1,
        bgcolor='rgba(0,0,0,0.5)'
    )
)

fig4.write_html('timeseries_04_monday_detail.html')
print("[OK] Created: timeseries_04_monday_detail.html")

# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "="*70)
print("DONE! Open the HTML files in your browser to explore.")
print("="*70)
print("\nGenerated Visualizations:")
print("  1. timeseries_01_all_zones.html - All 3 zones on one graph")
print("  2. timeseries_02_separate_panels.html - Stacked panels per zone")
print("  3. timeseries_03_weekly_patterns.html - Hourly patterns by day")
print("  4. timeseries_04_monday_detail.html - Single day with occupied hours")
print("\nThese are INTERACTIVE Grafana-style visualizations:")
print("  - Zoom: Click and drag")
print("  - Pan: Shift + click and drag")
print("  - Reset: Double-click")
print("  - Legend: Click to hide/show series")
print("  - Export: Camera icon (PNG, SVG, PDF)")
print("\n" + "="*70)
print("DEMO POINTS FOR DAN:")
print("="*70)
print("1. Generated programmatically (no UI configuration)")
print("2. Works directly from JSON (no database required)")
print("3. Claude Code can create custom analyses on demand")
print("4. Publication-ready quality")
print("5. Can be embedded in Jupyter notebooks for reproducible research")
print("\nTry asking Claude Code:")
print('  "Show correlation between Zone 1 and Zone 2 temps"')
print('  "Highlight times when temp exceeded 24degC"')
print('  "Calculate daily temperature range for each zone"')
