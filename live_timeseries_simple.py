"""
Live Time-Series Dashboard - Single Full-Screen Graph

Clean, full-screen visualization similar to newplot.png with:
- Single graph taking up entire viewport
- Compact header (title + last update on one line)
- Legend on right side, one item per line, limited width
- Zoom controls enabled
"""

import dash
from dash import dcc, html, callback_context
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
import json
import os
import re

# =============================================================================
# CONFIGURATION
# =============================================================================

INFLUXDB_CONFIG = {
    'url': 'http://localhost:8086',
    'token': 'bms-super-secret-token-change-in-production',
    'org': 'birdlab',
    'bucket': 'bms_data'
}

TIME_WINDOW = 72  # Hours of data to display (3 days)
MAX_SENSORS_UNFILTERED = 50  # Limit sensors when no filter active (for usability)

# Filter file path (set by filter interface)
FILTER_FILE = '/tmp/bms_filter_active.json'

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

# Set default Plotly template to dark (prevents white background during loading)
import plotly.io as pio
pio.templates.default = "plotly_dark"

# Add custom CSS to remove white borders and set black background
# CRITICAL: inline styles on body tag so background is dark BEFORE CSS loads
app.index_string = '''
<!DOCTYPE html>
<html style="background-color: #000000;">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <style>
            /* Set background BEFORE any other CSS loads */
            html, body {
                background-color: #000000 !important;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
            /* Make graph container grey during loading to match final state */
            #main-timeseries {
                background-color: #2D2D2D !important;
                min-height: calc(100vh - 42px);
            }
            .js-plotly-plot, .plotly, .plot-container, .svg-container {
                background-color: #2D2D2D !important;
            }
            /* Override any white backgrounds from Plotly during loading */
            div[data-dash-is-loading="true"] {
                background-color: #2D2D2D !important;
            }
            /* Ensure the entire dash app container is dark */
            #react-entry-point, ._dash-loading, #_dash-app-content {
                background-color: #000000 !important;
            }
        </style>
        {%css%}
    </head>
    <body style="background-color: #000000; margin: 0; padding: 0; overflow: hidden;">
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
            'fontSize': '12px',
            'flex': '1'  # Take remaining space
        }),
        html.Button("🔄 Refresh", id='refresh-btn', n_clicks=0, style={
            'color': '#00aaff',
            'fontSize': '14px',
            'background': 'transparent',
            'padding': '4px 12px',
            'border': '1px solid #00aaff',
            'borderRadius': '4px',
            'cursor': 'pointer',
            'marginRight': '10px'
        }),
        html.Button("Hide All", id='hide-all-btn', n_clicks=0, style={
            'fontSize': '12px',
            'background': 'transparent',
            'padding': '3px 8px',
            'borderRadius': '3px',
            'cursor': 'pointer',
            'marginRight': '5px'
        }),
        html.Button("Show All", id='show-all-btn', n_clicks=0, style={
            'fontSize': '12px',
            'background': 'transparent',
            'padding': '3px 8px',
            'borderRadius': '3px',
            'cursor': 'pointer',
            'marginRight': '10px'
        }),
        html.A("🔍 Filter Points", href="/filter/", target="_blank", style={
            'color': '#00aaff',
            'fontSize': '14px',
            'textDecoration': 'none',
            'padding': '4px 12px',
            'border': '1px solid #00aaff',
            'borderRadius': '4px',
            'marginLeft': '15px',
            'transition': 'background-color 0.2s'
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
            'width': '100%',
            'backgroundColor': '#2D2D2D'
        },
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['select2d', 'lasso2d']
        },
        figure={
            'data': [],
            'layout': {
                'paper_bgcolor': '#2D2D2D',
                'plot_bgcolor': '#1E1E1E',
                'xaxis': {'visible': False},
                'yaxis': {'visible': False},
                'margin': {'l': 0, 'r': 0, 't': 0, 'b': 0}
            }
        }
    ),

    # Stores
    dcc.Store(id='initial-load', data=True),
    dcc.Store(id='visibility-state', data='show')  # 'show' or 'hide'
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

def natural_sort_key(label):
    """Sort key that handles numbers properly (D1, D2, D10 not D1, D10, D2)"""
    parts = re.split(r'(\d+)', label)
    return [int(part) if part.isdigit() else part.lower() for part in parts]

def load_active_filter():
    """Load active filter from file if it exists"""
    try:
        if os.path.exists(FILTER_FILE):
            with open(FILTER_FILE, 'r') as f:
                return json.load(f).get('points', [])
        return None
    except Exception as e:
        print(f"Error loading filter: {e}")
        return None

def fetch_data_from_influxdb():
    """Fetch data from InfluxDB for the specified time window"""
    try:
        active_filter = load_active_filter()
        query_api = influx_client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_CONFIG['bucket']}")
          |> range(start: -{TIME_WINDOW}h)
          |> filter(fn: (r) => r._measurement == "bms_data")
          |> filter(fn: (r) => r.tenant_id == "sackville")
          |> filter(fn: (r) => r._field == "value")
        '''

        result = query_api.query(query, org=INFLUXDB_CONFIG['org'])

        # Convert to DataFrame
        data_points = []
        for table in result:
            for record in table.records:
                data_points.append({
                    'sensor': record.values.get('sensor_name'),
                    'value': record.get_value(),
                    'time': record.get_time()
                })

        df = pd.DataFrame(data_points)

        if df.empty:
            return df, datetime.now(), active_filter, False

        # Apply filter if exists
        if active_filter is not None:
            df = df[df['sensor'].isin(active_filter)]

        # ALWAYS enforce the sensor limit (even with filter)
        all_sensors = sorted(df['sensor'].unique(), key=natural_sort_key)
        if len(all_sensors) > MAX_SENSORS_UNFILTERED:
            limited_sensors = all_sensors[:MAX_SENSORS_UNFILTERED]
            df = df[df['sensor'].isin(limited_sensors)]
            is_limited = True
        else:
            is_limited = False

        return df, datetime.now(), active_filter, is_limited

    except Exception as e:
        print(f"Error fetching from InfluxDB: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), datetime.now(), None, False

# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    [Output('visibility-state', 'data'),
     Output('hide-all-btn', 'style'),
     Output('show-all-btn', 'style')],
    [Input('hide-all-btn', 'n_clicks'),
     Input('show-all-btn', 'n_clicks')],
    [State('visibility-state', 'data')]
)
def update_visibility(hide_clicks, show_clicks, current_state):
    """Update visibility state and button styles"""
    ctx = callback_context

    # Determine new state
    new_state = current_state
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'hide-all-btn':
            new_state = 'hide'
        elif button_id == 'show-all-btn':
            new_state = 'show'

    # Button styles - blue for available action, grey for current state
    base_style = {
        'fontSize': '12px',
        'background': 'transparent',
        'padding': '3px 8px',
        'borderRadius': '3px',
        'cursor': 'pointer',
        'marginRight': '5px'
    }
    blue_style = {**base_style, 'color': '#00aaff', 'border': '1px solid #00aaff'}
    grey_style = {**base_style, 'color': '#555', 'border': '1px solid #333', 'marginRight': '10px'}

    if new_state == 'show':
        # All visible - Hide All is the action, Show All is greyed
        return new_state, blue_style, {**grey_style, 'marginRight': '10px'}
    else:
        # All hidden - Show All is the action, Hide All is greyed
        return new_state, {**grey_style, 'marginRight': '5px'}, {**blue_style, 'marginRight': '10px'}

@app.callback(
    [Output('status', 'children'),
     Output('main-timeseries', 'figure')],
    [Input('refresh-btn', 'n_clicks'),
     Input('initial-load', 'data'),
     Input('visibility-state', 'data')]
)
def update_graph(n_clicks, initial, visibility_state):
    """Update the main graph"""
    df, timestamp, active_filter, is_limited = fetch_data_from_influxdb()

    # Status text
    num_sensors = df['sensor'].nunique() if not df.empty else 0
    if active_filter is not None and is_limited:
        status = f"{timestamp.strftime('%H:%M:%S')} | 🔍 FILTERED: {num_sensors} points (max {MAX_SENSORS_UNFILTERED} - refine filter)"
    elif active_filter is not None:
        status = f"{timestamp.strftime('%H:%M:%S')} | 🔍 FILTERED: {num_sensors} points"
    elif is_limited:
        status = f"{timestamp.strftime('%H:%M:%S')} | Showing first {num_sensors} points (use Filter for more)"
    else:
        status = f"{timestamp.strftime('%H:%M:%S')} | {num_sensors} points"

    # Create figure
    fig = go.Figure()
    colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', '#F38181',
              '#AA96DA', '#FCBAD3', '#A8D8EA', '#FF8B94', '#C7CEEA']

    if not df.empty:
        sorted_sensors = sorted(df['sensor'].unique(), key=natural_sort_key)
        # Set visibility based on state
        trace_visible = True if visibility_state == 'show' else 'legendonly'

        for i, sensor in enumerate(sorted_sensors):
            sensor_df = df[df['sensor'] == sensor].sort_values('time')
            fig.add_trace(go.Scatter(
                x=sensor_df['time'],
                y=sensor_df['value'],
                name=sensor,
                uid=sensor,
                visible=trace_visible,
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=1.5),
                legendrank=i,
                hovertemplate='<b>%{fullData.name}</b><br>Time: %{x|%H:%M:%S}<br>Value: %{y:.2f}<extra></extra>'
            ))

    # Layout - single update_layout call
    fig.update_layout(
        margin=dict(l=50, r=200, t=40, b=40),
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#2D2D2D',
        font=dict(color='#e0e0e0', size=11),
        uirevision='constant',
        hovermode='closest',
        hoverlabel=dict(bgcolor='#1a1a1a', font_size=11),
        dragmode='pan',
        xaxis=dict(
            title='',
            gridcolor='#333333',
            showgrid=True,
            zeroline=False,
            color='#E0E0E0',
            fixedrange=False,
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
                x=0, y=1.08, xanchor='left', yanchor='top'
            )
        ),
        yaxis=dict(
            title=dict(text='Value', font=dict(size=12)),
            gridcolor='#333333',
            showgrid=True,
            zeroline=False,
            color='#E0E0E0',
            fixedrange=False,
            autorange=True
        ),
        legend=dict(
            orientation='v',
            yanchor='top', y=1,
            xanchor='left', x=1.01,
            bgcolor='rgba(0,0,0,0.8)',
            bordercolor='#333',
            borderwidth=1,
            font=dict(size=10),
            itemsizing='constant',
            tracegroupgap=2,
            itemclick='toggle',
            itemdoubleclick='toggleothers'
        )
    )

    return status, fig

# =============================================================================
# RUN
# =============================================================================

if __name__ == '__main__':
    print(f"Dashboard: http://localhost:8050 | {TIME_WINDOW}h window | {MAX_SENSORS_UNFILTERED} sensor limit")
    app.run(debug=False, host='0.0.0.0', port=8050)
