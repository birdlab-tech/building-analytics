"""
Real-Time BMS Dashboard - Auto-Refreshing Plotly Dash Application

This creates a live, auto-refreshing dashboard that pulls data from:
- Option 1: Direct API calls (no database required)
- Option 2: InfluxDB time-series data (for historical trends)

Run this and open http://localhost:8050 in your browser.
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
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

# Initialize BMS API client
bms_client = BMSAPIClient(BMS_CONFIG['url'], BMS_CONFIG['token'])

# =============================================================================
# DASH APP SETUP
# =============================================================================

app = dash.Dash(__name__)
app.title = "Live BMS Dashboard"

# =============================================================================
# LAYOUT
# =============================================================================

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🔴 LIVE BMS Dashboard", style={
            'color': '#00aaff',
            'textAlign': 'center',
            'marginBottom': '10px'
        }),
        html.P(id='last-update', style={
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

    # Stats Cards
    html.Div(id='stats-cards', style={
        'display': 'flex',
        'justifyContent': 'space-around',
        'marginBottom': '20px',
        'flexWrap': 'wrap'
    }),

    # Main Charts
    html.Div([
        # System Overview
        dcc.Graph(id='system-overview', style={'marginBottom': '20px'}),

        # Two-column layout for detailed charts
        html.Div([
            html.Div([
                dcc.Graph(id='pump-speeds')
            ], style={'width': '50%', 'display': 'inline-block'}),

            html.Div([
                dcc.Graph(id='valve-positions')
            ], style={'width': '50%', 'display': 'inline-block'})
        ]),

        # AHU Status
        dcc.Graph(id='ahu-status', style={'marginTop': '20px'})
    ]),

    # Auto-refresh interval
    dcc.Interval(
        id='interval-component',
        interval=REFRESH_INTERVAL,  # in milliseconds
        n_intervals=0
    )
], style={
    'backgroundColor': '#0a0a0a',
    'color': '#e0e0e0',
    'padding': '20px',
    'fontFamily': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
    'minHeight': '100vh'
})

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def fetch_live_data():
    """Fetch current data from BMS API"""
    try:
        data = bms_client.fetch_and_parse()
        df = pd.DataFrame(data)
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def categorize_system(label):
    """Categorize BMS point by system"""
    label_lower = label.lower()
    if 'chw' in label_lower or 'chiller' in label_lower:
        return 'Chiller'
    elif 'lphw' in label_lower or 'heating' in label_lower:
        return 'Heating'
    elif 'ahu' in label_lower:
        return 'AHU'
    elif 'pump' in label_lower:
        return 'Pump'
    elif 'valve' in label_lower:
        return 'Valve'
    else:
        return 'Other'

# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    [Output('last-update', 'children'),
     Output('stats-cards', 'children'),
     Output('system-overview', 'figure'),
     Output('pump-speeds', 'figure'),
     Output('valve-positions', 'figure'),
     Output('ahu-status', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    """Update all dashboard components"""

    # Fetch live data
    df = fetch_live_data()

    if df.empty:
        # Return empty figures if no data
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template='plotly_dark',
            title='No data available'
        )
        return (
            "No data available",
            [],
            empty_fig, empty_fig, empty_fig, empty_fig
        )

    # Add system categorization
    df['System'] = df['Label'].apply(categorize_system)

    # Last update time
    last_update = f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # =============================================================================
    # STATS CARDS
    # =============================================================================

    total_points = len(df)
    systems = df['System'].nunique()
    avg_value = df['Value'].mean()

    # Count active pumps
    pumps = df[df['Label'].str.contains('Pump', case=False, na=False)]
    active_pumps = len(pumps[pumps['Value'] > 0])

    stats_cards = [
        # Total Points
        html.Div([
            html.H3(f"{total_points}", style={'margin': '0', 'color': '#00aaff'}),
            html.P("Total Points", style={'margin': '0', 'color': '#888'})
        ], style={
            'background': '#1a1a1a',
            'padding': '20px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'minWidth': '150px',
            'margin': '10px'
        }),

        # Systems
        html.Div([
            html.H3(f"{systems}", style={'margin': '0', 'color': '#00aaff'}),
            html.P("Systems", style={'margin': '0', 'color': '#888'})
        ], style={
            'background': '#1a1a1a',
            'padding': '20px',
            'borderRadius': '8px',
            'textAlign': 'center',
            'minWidth': '150px',
            'margin': '10px'
        }),

        # Active Pumps
        html.Div([
            html.H3(f"{active_pumps}/{len(pumps)}", style={'margin': '0', 'color': '#4ECDC4'}),
            html.P("Pumps Active", style={'margin': '0', 'color': '#888'})
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
    # SYSTEM OVERVIEW
    # =============================================================================

    system_counts = df.groupby('System').size().reset_index(name='Count')

    fig_overview = go.Figure(data=[
        go.Bar(
            x=system_counts['System'],
            y=system_counts['Count'],
            marker_color='#00aaff',
            text=system_counts['Count'],
            textposition='outside'
        )
    ])

    fig_overview.update_layout(
        template='plotly_dark',
        title='Points by System Type',
        xaxis_title='System',
        yaxis_title='Number of Points',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#2D2D2D'
    )

    # =============================================================================
    # PUMP SPEEDS
    # =============================================================================

    pump_data = df[df['Label'].str.contains('Pump.*Speed', case=False, regex=True, na=False)]

    fig_pumps = go.Figure(data=[
        go.Bar(
            x=pump_data['Label'].str.replace(r'L\d+_O\d+_D\d+_', '', regex=True),
            y=pump_data['Value'],
            marker_color=['#4ECDC4' if v > 0 else '#666' for v in pump_data['Value']],
            text=[f"{v:.1f}%" for v in pump_data['Value']],
            textposition='outside'
        )
    ])

    fig_pumps.update_layout(
        template='plotly_dark',
        title='Pump Speeds',
        xaxis_title='Pump',
        yaxis_title='Speed (%)',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#2D2D2D',
        xaxis_tickangle=-45,
        height=400
    )

    # =============================================================================
    # VALVE POSITIONS
    # =============================================================================

    valve_data = df[df['Label'].str.contains('Valve', case=False, na=False)]

    # Show top 10 active valves
    top_valves = valve_data.nlargest(10, 'Value')

    fig_valves = go.Figure(data=[
        go.Bar(
            x=top_valves['Label'].str.replace(r'L\d+_O\d+_D\d+_', '', regex=True),
            y=top_valves['Value'],
            marker_color='#FFE66D',
            text=[f"{v:.1f}%" for v in top_valves['Value']],
            textposition='outside'
        )
    ])

    fig_valves.update_layout(
        template='plotly_dark',
        title='Top 10 Active Valves',
        xaxis_title='Valve',
        yaxis_title='Position (%)',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#2D2D2D',
        xaxis_tickangle=-45,
        height=400
    )

    # =============================================================================
    # AHU STATUS
    # =============================================================================

    ahu_data = df[df['Label'].str.contains('AHU', case=False, na=False)]

    # Group AHU data by AHU number
    ahu_htg = ahu_data[ahu_data['Label'].str.contains('Htg Valve', case=False, na=False)]
    ahu_clg = ahu_data[ahu_data['Label'].str.contains('Clg Valve', case=False, na=False)]

    fig_ahu = go.Figure()

    fig_ahu.add_trace(go.Bar(
        name='Heating Valves',
        x=ahu_htg['Label'].str.replace(r'L\d+_O\d+_D\d+_', '', regex=True),
        y=ahu_htg['Value'],
        marker_color='#FF6B6B',
        text=[f"{v:.1f}%" for v in ahu_htg['Value']],
        textposition='outside'
    ))

    fig_ahu.add_trace(go.Bar(
        name='Cooling Valves',
        x=ahu_clg['Label'].str.replace(r'L\d+_O\d+_D\d+_', '', regex=True),
        y=ahu_clg['Value'],
        marker_color='#4ECDC4',
        text=[f"{v:.1f}%" for v in ahu_clg['Value']],
        textposition='outside'
    ))

    fig_ahu.update_layout(
        template='plotly_dark',
        title='AHU Heating vs Cooling',
        xaxis_title='AHU Valve',
        yaxis_title='Position (%)',
        barmode='group',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#2D2D2D',
        xaxis_tickangle=-45,
        height=500
    )

    return last_update, stats_cards, fig_overview, fig_pumps, fig_valves, fig_ahu


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == '__main__':
    print("="*70)
    print("STARTING LIVE BMS DASHBOARD")
    print("="*70)
    print(f"BMS API: {BMS_CONFIG['url']}")
    print(f"Refresh Interval: {REFRESH_INTERVAL/1000} seconds")
    print("\nOpen your browser to: http://localhost:8050")
    print("\nPress Ctrl+C to stop")
    print("="*70)

    app.run(debug=True, host='0.0.0.0', port=8050)
