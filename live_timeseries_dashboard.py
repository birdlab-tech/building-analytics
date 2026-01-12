"""
Live Time-Series Dashboard - Grafana-Style Line Graphs

This dashboard accumulates data over time and displays it as trending line graphs,
similar to timeseries_01_all_zones.html but with LIVE data that updates automatically.

Run this and open http://localhost:8050 in your browser.
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from collections import deque
from live_api_client import BMSAPIClient

# =============================================================================
# CONFIGURATION
# =============================================================================

# BMS API Configuration
BMS_CONFIG = {
    'url': 'https://192.168.11.128/rest',
    'token': '6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji'
}

# Dashboard Configuration
REFRESH_INTERVAL = 15000  # Refresh every 15 seconds (in milliseconds)
MAX_HISTORY_POINTS = 200  # Keep last 200 data points per sensor (~50 minutes at 15s intervals)

# Initialize BMS API client
bms_client = BMSAPIClient(BMS_CONFIG['url'], BMS_CONFIG['token'])

# Data storage (persists between updates)
# Format: {label: deque([(timestamp, value), ...], maxlen=MAX_HISTORY_POINTS)}
historical_data = {}

# =============================================================================
# GRAFANA-STYLE THEME
# =============================================================================

DARK_THEME = {
    'plot_bgcolor': '#1E1E1E',
    'paper_bgcolor': '#2D2D2D',
    'font_color': '#E0E0E0',
    'grid_color': '#333333',
    'title_color': '#00aaff'
}

# =============================================================================
# DASH APP SETUP
# =============================================================================

app = dash.Dash(__name__)
app.title = "Live Time-Series Dashboard"

# =============================================================================
# LAYOUT
# =============================================================================

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🔴 LIVE Time-Series Dashboard", style={
            'color': DARK_THEME['title_color'],
            'textAlign': 'center',
            'marginBottom': '10px'
        }),
        html.P(id='last-update-ts', style={
            'color': '#888',
            'textAlign': 'center',
            'fontSize': '14px'
        })
    ], style={
        'background': 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)',
        'padding': '20px',
        'borderRadius': '10px',
        'marginBottom': '20px',
        'border': '2px solid #00aaff'
    }),

    # Stats
    html.Div(id='stats-ts', style={
        'display': 'flex',
        'justifyContent': 'space-around',
        'marginBottom': '20px',
        'flexWrap': 'wrap'
    }),

    # Time-Series Charts
    html.Div([
        # Pump Speeds Over Time
        dcc.Graph(id='pumps-timeseries', style={'marginBottom': '20px'}),

        # Valve Positions Over Time
        dcc.Graph(id='valves-timeseries', style={'marginBottom': '20px'}),

        # AHU Valves Over Time
        dcc.Graph(id='ahu-timeseries')
    ]),

    # Auto-refresh interval
    dcc.Interval(
        id='interval-timeseries',
        interval=REFRESH_INTERVAL,
        n_intervals=0
    )
], style={
    'backgroundColor': '#000000',
    'color': DARK_THEME['font_color'],
    'padding': '20px',
    'fontFamily': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
    'minHeight': '100vh'
})

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def fetch_and_store_data():
    """Fetch current data and add to historical storage"""
    try:
        # Fetch current data
        data = bms_client.fetch_and_parse()
        df = pd.DataFrame(data)
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')

        # Current timestamp
        timestamp = datetime.now()

        # Store each point in historical data
        for _, row in df.iterrows():
            label = row['Label']
            value = row['Value']

            # Initialize deque if first time seeing this label
            if label not in historical_data:
                historical_data[label] = deque(maxlen=MAX_HISTORY_POINTS)

            # Append new data point
            historical_data[label].append((timestamp, value))

        return df, timestamp

    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame(), datetime.now()

def get_timeseries(labels_pattern):
    """
    Get time-series data for labels matching pattern
    Returns: dict of {label: (timestamps, values)}
    """
    result = {}

    for label, data_points in historical_data.items():
        if labels_pattern.lower() in label.lower():
            if len(data_points) > 0:
                timestamps = [point[0] for point in data_points]
                values = [point[1] for point in data_points]
                result[label] = (timestamps, values)

    return result

# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    [Output('last-update-ts', 'children'),
     Output('stats-ts', 'children'),
     Output('pumps-timeseries', 'figure'),
     Output('valves-timeseries', 'figure'),
     Output('ahu-timeseries', 'figure')],
    [Input('interval-timeseries', 'n_intervals')]
)
def update_timeseries_dashboard(n):
    """Update all time-series components"""

    # Fetch and store new data
    df, timestamp = fetch_and_store_data()

    if df.empty:
        # Return empty figures if no data
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template='plotly_dark',
            title='No data available',
            plot_bgcolor=DARK_THEME['plot_bgcolor'],
            paper_bgcolor=DARK_THEME['paper_bgcolor']
        )
        return (
            "No data available",
            [],
            empty_fig, empty_fig, empty_fig
        )

    # Last update time
    last_update = f"Last Update: {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | Data Points Stored: {len(historical_data)}"

    # =============================================================================
    # STATS CARDS
    # =============================================================================

    total_labels = len(historical_data)
    total_history = sum(len(data) for data in historical_data.values())
    duration_minutes = max(
        [len(data) * (REFRESH_INTERVAL / 1000 / 60) for data in historical_data.values()]
        if historical_data else [0]
    )

    stats_cards = [
        html.Div([
            html.H3(f"{total_labels}", style={'margin': '0', 'color': DARK_THEME['title_color']}),
            html.P("Tracked Sensors", style={'margin': '0', 'color': '#888'})
        ], style={
            'background': '#1a1a1a',
            'padding': '20px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'minWidth': '150px',
            'margin': '10px'
        }),

        html.Div([
            html.H3(f"{total_history}", style={'margin': '0', 'color': DARK_THEME['title_color']}),
            html.P("Total Data Points", style={'margin': '0', 'color': '#888'})
        ], style={
            'background': '#1a1a1a',
            'padding': '20px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'minWidth': '150px',
            'margin': '10px'
        }),

        html.Div([
            html.H3(f"{duration_minutes:.1f}", style={'margin': '0', 'color': '#4ECDC4'}),
            html.P("Minutes of History", style={'margin': '0', 'color': '#888'})
        ], style={
            'background': '#1a1a1a',
            'padding': '20px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'minWidth': '150px',
            'margin': '10px'
        })
    ]

    # =============================================================================
    # PUMP SPEEDS TIME-SERIES
    # =============================================================================

    pump_series = get_timeseries('Pump')

    fig_pumps = go.Figure()

    colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', '#F38181']

    for i, (label, (timestamps, values)) in enumerate(pump_series.items()):
        # Shorten label for legend
        short_label = label.split('_', 3)[-1] if '_' in label else label

        fig_pumps.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            name=short_label,
            mode='lines',
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Time: %{x|%H:%M:%S}<br>' +
                          'Speed: %{y:.1f}%<br>' +
                          '<extra></extra>'
        ))

    fig_pumps.update_layout(
        title='Pump Speeds Over Time',
        xaxis=dict(
            title='Time',
            gridcolor=DARK_THEME['grid_color'],
            color=DARK_THEME['font_color'],
            showgrid=True
        ),
        yaxis=dict(
            title='Speed (%)',
            gridcolor=DARK_THEME['grid_color'],
            color=DARK_THEME['font_color'],
            showgrid=True
        ),
        plot_bgcolor=DARK_THEME['plot_bgcolor'],
        paper_bgcolor=DARK_THEME['paper_bgcolor'],
        font=dict(color=DARK_THEME['font_color']),
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(0,0,0,0.5)'
        ),
        height=400
    )

    # =============================================================================
    # VALVE POSITIONS TIME-SERIES
    # =============================================================================

    valve_series = get_timeseries('Valve')

    # Limit to top 5 most active valves (highest average value)
    valve_avgs = {}
    for label, (timestamps, values) in valve_series.items():
        if len(values) > 0:
            valve_avgs[label] = sum(values) / len(values)

    top_valves = sorted(valve_avgs.items(), key=lambda x: x[1], reverse=True)[:5]

    fig_valves = go.Figure()

    for i, (label, avg_val) in enumerate(top_valves):
        timestamps, values = valve_series[label]
        short_label = label.split('_', 3)[-1] if '_' in label else label

        fig_valves.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            name=short_label,
            mode='lines',
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Time: %{x|%H:%M:%S}<br>' +
                          'Position: %{y:.1f}%<br>' +
                          '<extra></extra>'
        ))

    fig_valves.update_layout(
        title='Top 5 Active Valves Over Time',
        xaxis=dict(
            title='Time',
            gridcolor=DARK_THEME['grid_color'],
            color=DARK_THEME['font_color'],
            showgrid=True
        ),
        yaxis=dict(
            title='Position (%)',
            gridcolor=DARK_THEME['grid_color'],
            color=DARK_THEME['font_color'],
            showgrid=True
        ),
        plot_bgcolor=DARK_THEME['plot_bgcolor'],
        paper_bgcolor=DARK_THEME['paper_bgcolor'],
        font=dict(color=DARK_THEME['font_color']),
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(0,0,0,0.5)'
        ),
        height=400
    )

    # =============================================================================
    # AHU TIME-SERIES
    # =============================================================================

    ahu_htg_series = get_timeseries('Htg Valve')
    ahu_clg_series = get_timeseries('Clg Valve')

    fig_ahu = go.Figure()

    # Add heating valves (red tones)
    for i, (label, (timestamps, values)) in enumerate(list(ahu_htg_series.items())[:3]):
        short_label = label.split('_', 3)[-1] if '_' in label else label

        fig_ahu.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            name=f"{short_label} (Heating)",
            mode='lines',
            line=dict(color='#FF6B6B', width=2, dash=['solid', 'dash', 'dot'][i]),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Time: %{x|%H:%M:%S}<br>' +
                          'Position: %{y:.1f}%<br>' +
                          '<extra></extra>'
        ))

    # Add cooling valves (blue tones)
    for i, (label, (timestamps, values)) in enumerate(list(ahu_clg_series.items())[:3]):
        short_label = label.split('_', 3)[-1] if '_' in label else label

        fig_ahu.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            name=f"{short_label} (Cooling)",
            mode='lines',
            line=dict(color='#4ECDC4', width=2, dash=['solid', 'dash', 'dot'][i]),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                          'Time: %{x|%H:%M:%S}<br>' +
                          'Position: %{y:.1f}%<br>' +
                          '<extra></extra>'
        ))

    fig_ahu.update_layout(
        title='AHU Heating vs Cooling Valves Over Time',
        xaxis=dict(
            title='Time',
            gridcolor=DARK_THEME['grid_color'],
            color=DARK_THEME['font_color'],
            showgrid=True
        ),
        yaxis=dict(
            title='Position (%)',
            gridcolor=DARK_THEME['grid_color'],
            color=DARK_THEME['font_color'],
            showgrid=True
        ),
        plot_bgcolor=DARK_THEME['plot_bgcolor'],
        paper_bgcolor=DARK_THEME['paper_bgcolor'],
        font=dict(color=DARK_THEME['font_color']),
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(0,0,0,0.5)'
        ),
        height=500
    )

    return last_update, stats_cards, fig_pumps, fig_valves, fig_ahu


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == '__main__':
    print("="*70)
    print("STARTING LIVE TIME-SERIES DASHBOARD (GRAFANA STYLE)")
    print("="*70)
    print(f"BMS API: {BMS_CONFIG['url']}")
    print(f"Refresh Interval: {REFRESH_INTERVAL/1000} seconds")
    print(f"History Buffer: {MAX_HISTORY_POINTS} points per sensor")
    print(f"  (~{MAX_HISTORY_POINTS * REFRESH_INTERVAL / 1000 / 60:.0f} minutes of history)")
    print("\nOpen your browser to: http://localhost:8050")
    print("\nThe dashboard will build up history as it runs.")
    print("Leave it running to see trends develop!")
    print("\nPress Ctrl+C to stop")
    print("="*70)

    app.run(debug=True, host='0.0.0.0', port=8050)
