"""
Live Time-Series Dashboard - Single Full-Screen Graph

Clean, full-screen visualization similar to newplot.png with:
- Single graph taking up entire viewport
- Compact header (title + last update on one line)
- Legend on right side, one item per line, limited width
- Zoom controls enabled
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient

# =============================================================================
# CONFIGURATION
# =============================================================================

INFLUXDB_CONFIG = {
    'url': 'http://localhost:8086',
    'token': 'bms-super-secret-token-change-in-production',
    'org': 'birdlab',
    'bucket': 'bms_data'
}

REFRESH_INTERVAL = 60000  # 1 minute (reading from local database is fast)
TIME_WINDOW = 24  # Hours of data to display (can show more since it's from database)

# Filter which points to track (to reduce clutter)
# Options: 'all', 'pumps', 'valves', 'ahu', 'temp'
TRACK_FILTER = 'all'

influx_client = InfluxDBClient(
    url=INFLUXDB_CONFIG['url'],
    token=INFLUXDB_CONFIG['token'],
    org=INFLUXDB_CONFIG['org']
)

# =============================================================================
# APP SETUP
# =============================================================================

app = dash.Dash(__name__)
app.title = "Live BMS Time-Series"

# Add custom CSS to remove white borders and set black background
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                background-color: #000000;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# =============================================================================
# LAYOUT - MINIMAL & CLEAN
# =============================================================================

app.layout = html.Div([
    # Compact header - title and status
    html.Div([
        html.Span("🔴 LIVE BMS Time-Series", style={
            'color': '#00aaff',
            'fontSize': '16px',
            'fontWeight': 'bold',
            'marginRight': '20px'
        }),
        html.Span(id='status', style={
            'color': '#888',
            'fontSize': '12px'
        })
    ], style={
        'background': '#1a1a1a',
        'padding': '8px 15px',
        'borderBottom': '1px solid #333',
        'display': 'flex',
        'alignItems': 'center'
    }),

    # Full-screen graph
    dcc.Graph(
        id='main-timeseries',
        style={
            'height': 'calc(100vh - 42px)',  # Full height minus header
            'width': '100%'
        },
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['select2d', 'lasso2d']
        }
    ),

    # Auto-refresh (n_intervals=0 triggers immediately on load, then every REFRESH_INTERVAL)
    dcc.Interval(
        id='interval',
        interval=REFRESH_INTERVAL,
        n_intervals=0  # Starts at 0, triggers callback immediately
    )
], style={
    'backgroundColor': '#000000',
    'margin': '0',
    'padding': '0',
    'height': '100vh',
    'overflow': 'hidden',
    'fontFamily': 'Segoe UI, sans-serif'
})

# =============================================================================
# DATA MANAGEMENT
# =============================================================================

def should_track_point(label):
    """Filter which points to track based on TRACK_FILTER"""
    if TRACK_FILTER == 'all':
        return True

    label_lower = label.lower()

    if TRACK_FILTER == 'pumps':
        return 'pump' in label_lower
    elif TRACK_FILTER == 'valves':
        return 'valve' in label_lower
    elif TRACK_FILTER == 'ahu':
        return 'ahu' in label_lower
    elif TRACK_FILTER == 'temp':
        return 'temp' in label_lower

    return True

def fetch_data_from_influxdb():
    """Fetch data from InfluxDB for the specified time window"""
    try:
        query_api = influx_client.query_api()

        # Query last TIME_WINDOW hours of data for Sackville building
        query = f'''
        from(bucket: "{INFLUXDB_CONFIG['bucket']}")
          |> range(start: -{TIME_WINDOW}h)
          |> filter(fn: (r) => r._measurement == "bms_data")
          |> filter(fn: (r) => r.tenant_id == "sackville")
          |> filter(fn: (r) => r._field == "value")
        '''

        result = query_api.query(query, org=INFLUXDB_CONFIG['org'])

        # Convert to pandas DataFrame
        data_points = []
        for table in result:
            for record in table.records:
                sensor_name = record.values.get('sensor_name')
                value = record.get_value()
                time = record.get_time()

                # Apply filter
                if should_track_point(sensor_name):
                    data_points.append({
                        'sensor': sensor_name,
                        'value': value,
                        'time': time
                    })

        df = pd.DataFrame(data_points)
        return df, datetime.now()

    except Exception as e:
        print(f"Error fetching from InfluxDB: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), datetime.now()

# =============================================================================
# CALLBACK
# =============================================================================

@app.callback(
    [Output('status', 'children'),
     Output('main-timeseries', 'figure')],
    [Input('interval', 'n_intervals')]
)
def update_graph(n):
    """Update the main graph"""

    # Fetch data from InfluxDB
    df, timestamp = fetch_data_from_influxdb()

    # Status text
    unique_points = df['sensor'].nunique() if not df.empty else 0
    total_datapoints = len(df)
    status = f"Last Update: {timestamp.strftime('%H:%M:%S')} | {unique_points} points | {total_datapoints} polls ({TIME_WINDOW}h window)"

    # Create figure
    fig = go.Figure()

    # Color palette
    colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', '#F38181',
              '#AA96DA', '#FCBAD3', '#A8D8EA', '#FF8B94', '#C7CEEA']

    # Natural sort key function - handles numbers properly (D1, D2, D3... not D1, D21, D22, D2, D3)
    import re
    def natural_sort_key(label):
        # Split into text and number parts
        parts = re.split(r'(\d+)', label)
        # Convert numeric parts to integers for proper sorting
        return [int(part) if part.isdigit() else part.lower() for part in parts]

    # Group data by sensor and sort
    if not df.empty:
        sensors_data = {}
        for sensor in df['sensor'].unique():
            sensor_df = df[df['sensor'] == sensor].sort_values('time')
            sensors_data[sensor] = sensor_df

        # Sort sensors by natural order
        sorted_sensors = sorted(sensors_data.keys(), key=natural_sort_key)

        # Add all sensors with data
        color_idx = 0
        for sensor in sorted_sensors:
            sensor_df = sensors_data[sensor]

            fig.add_trace(go.Scatter(
                x=sensor_df['time'],
                y=sensor_df['value'],
                name=sensor,  # Always show full sensor name
                mode='lines',
                line=dict(
                    color=colors[color_idx % len(colors)],
                    width=1.5
                ),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Time: %{x|%H:%M:%S}<br>' +
                              'Value: %{y:.2f}<br>' +
                              '<extra></extra>'
            ))

            color_idx += 1

    # Layout - maximize graph space
    fig.update_layout(
        # No title - we have it in the header
        margin=dict(l=50, r=200, t=40, b=40),  # Top margin for buttons
        plot_bgcolor='#1E1E1E',  # Dark gray for plot area (matches visualize_timeseries.py)
        paper_bgcolor='#2D2D2D',  # Slightly lighter gray for figure (matches visualize_timeseries.py)
        font=dict(color='#e0e0e0', size=11),

        # Preserve user interactions (zoom, pan, legend selections) across updates
        uirevision='constant',

        # X-axis - fixed range controls
        xaxis=dict(
            title='',
            gridcolor='#333333',  # Medium gray grid (matches visualize_timeseries.py)
            showgrid=True,
            zeroline=False,
            color='#E0E0E0',
            fixedrange=False,  # Allow zooming
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1h", step="hour", stepmode="backward"),
                    dict(count=3, label="3h", step="hour", stepmode="backward"),
                    dict(count=6, label="6h", step="hour", stepmode="backward"),
                    dict(count=12, label="12h", step="hour", stepmode="backward"),
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=3, label="3d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(step="all", label="All")
                ],
                bgcolor='#1a1a1a',
                activecolor='#00aaff',
                font=dict(color='#e0e0e0', size=10),
                x=0,
                y=1.08,
                xanchor='left',
                yanchor='top'
            )
        ),

        # Y-axis - auto-scale based on visible data
        yaxis=dict(
            title=dict(text='Value', font=dict(size=12)),
            gridcolor='#333333',  # Medium gray grid (matches visualize_timeseries.py)
            showgrid=True,
            zeroline=False,
            color='#E0E0E0',
            fixedrange=False,  # Allow auto-scaling
            autorange=True  # Auto-fit to data
        ),

        # Legend - on the right side, vertical, limited width
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.01,
            bgcolor='rgba(0,0,0,0.8)',
            bordercolor='#333',
            borderwidth=1,
            font=dict(size=10),
            itemsizing='constant',
            tracegroupgap=2,
            # Enable grouped legend interactions
            groupclick='toggleitem'
        ),

        # Hover settings - closest point only (less sticky)
        hovermode='closest',
        hoverlabel=dict(
            bgcolor='#1a1a1a',
            font_size=11
        ),

        # Drag to pan (easier than zoom for time-series)
        dragmode='pan',

        # Add custom buttons for legend control
        updatemenus=[
            dict(
                type='buttons',
                direction='left',
                x=0.5,
                y=1.08,
                xanchor='center',
                yanchor='top',
                showactive=False,
                buttons=[
                    dict(
                        label='Show All',
                        method='restyle',
                        args=['visible', True]
                    ),
                    dict(
                        label='Hide All',
                        method='restyle',
                        args=['visible', 'legendonly']
                    )
                ],
                bgcolor='#1a1a1a',
                bordercolor='#333',
                font=dict(color='#e0e0e0', size=10)
            )
        ]
    )

    return status, fig

# =============================================================================
# RUN
# =============================================================================

if __name__ == '__main__':
    print("="*70)
    print("LIVE TIME-SERIES DASHBOARD - INFLUXDB")
    print("="*70)
    print(f"Open: http://localhost:8050")
    print(f"Data Source: InfluxDB @ {INFLUXDB_CONFIG['url']}")
    print(f"Building: Sackville | Time Window: {TIME_WINDOW}h")
    print(f"Refresh: {REFRESH_INTERVAL/1000:.0f} seconds | Filter: {TRACK_FILTER}")
    print("\nFirst load happens immediately when you open the page!")
    print("\nTime Range Buttons (top left):")
    print("  - 1h, 3h, 6h, 12h, 1d, 3d, 1w, All")
    print("\nLegend Controls (top center):")
    print("  - 'Show All' button - shows all traces")
    print("  - 'Hide All' button - hides all traces")
    print("  - Click legend item - toggle individual trace")
    print("  - Double-click legend item - isolate that trace only")
    print("\nGraph Controls:")
    print("  - Pan: Click and drag on graph")
    print("  - Zoom: Use scroll wheel OR box zoom (toolbar)")
    print("  - Reset: Double-click graph")
    print("  - Y-axis auto-scales to visible data")
    print("\nData Collection:")
    print(f"  - Background collector polls BMS every 5 minutes")
    print(f"  - Dashboard reads from InfluxDB (fast local queries)")
    print(f"  - Currently showing last {TIME_WINDOW}h of data")
    print("  - To reduce clutter: change TRACK_FILTER to 'pumps' or 'valves'")
    print("\nPress Ctrl+C to stop")
    print("="*70)

    app.run(debug=True, host='0.0.0.0', port=8050)
