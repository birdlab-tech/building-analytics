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
from datetime import datetime
from collections import deque
from live_api_client import BMSAPIClient

# =============================================================================
# CONFIGURATION
# =============================================================================

BMS_CONFIG = {
    'url': 'https://192.168.11.128/rest',
    'token': '6r1lkFI2qDKrghg0YaeHMZF1Pbtbloji'
}

REFRESH_INTERVAL = 300000  # 5 minutes (safe for real BMS - standard polling interval)
MAX_HISTORY_POINTS = 1000  # ~3.5 days of history at 5-minute intervals

# Filter which points to track (to reduce clutter and network load)
# Options: 'all', 'pumps', 'valves', 'ahu', 'temp'
TRACK_FILTER = 'all'  # Change to 'pumps' or 'valves' to reduce point count

bms_client = BMSAPIClient(BMS_CONFIG['url'], BMS_CONFIG['token'])
historical_data = {}

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
    # Compact header - title, status, and label toggle on one line
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
            'marginRight': '20px'
        }),
        html.Button(
            'Show Full Labels',
            id='label-toggle',
            n_clicks=0,
            style={
                'background': '#333',
                'color': '#e0e0e0',
                'border': '1px solid #555',
                'padding': '4px 12px',
                'borderRadius': '4px',
                'fontSize': '11px',
                'cursor': 'pointer',
                'marginLeft': 'auto'
            }
        )
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

def fetch_and_store_data():
    """Fetch current data and add to historical storage"""
    try:
        data = bms_client.fetch_and_parse()
        df = pd.DataFrame(data)
        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')

        timestamp = datetime.now()
        stored_count = 0

        for _, row in df.iterrows():
            label = row['Label']
            value = row['Value']

            # Apply filter
            if not should_track_point(label):
                continue

            if label not in historical_data:
                historical_data[label] = deque(maxlen=MAX_HISTORY_POINTS)

            historical_data[label].append((timestamp, value))
            stored_count += 1

        return stored_count, timestamp
    except Exception as e:
        print(f"Error: {e}")
        return 0, datetime.now()

# =============================================================================
# CALLBACK
# =============================================================================

@app.callback(
    [Output('status', 'children'),
     Output('main-timeseries', 'figure'),
     Output('label-toggle', 'children')],
    [Input('interval', 'n_intervals'),
     Input('label-toggle', 'n_clicks')]
)
def update_graph(n, toggle_clicks):
    """Update the main graph"""

    # Determine if we should show full labels based on toggle clicks
    show_full_labels = (toggle_clicks % 2) == 1  # Odd clicks = full labels

    # Fetch new data (always runs, including at n=0 which is startup)
    point_count, timestamp = fetch_and_store_data()

    # Status text
    status = f"Last Update: {timestamp.strftime('%H:%M:%S')} | {len(historical_data)} sensors | {point_count} points"

    # Create figure
    fig = go.Figure()

    # Color palette
    colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', '#F38181',
              '#AA96DA', '#FCBAD3', '#A8D8EA', '#FF8B94', '#C7CEEA']

    # Function to get display label based on toggle state
    def get_display_label(label):
        if show_full_labels:
            return label  # Show full label with L11_O11_D1_ prefix
        else:
            # Shorten label - remove prefix
            return label.split('_', 3)[-1] if label.count('_') >= 3 else label

    # Natural sort key function - handles numbers properly (D1, D2, D3... not D1, D21, D22, D2, D3)
    import re
    def natural_sort_key(label):
        display_label = get_display_label(label)
        # Split into text and number parts
        parts = re.split(r'(\d+)', display_label)
        # Convert numeric parts to integers for proper sorting
        return [int(part) if part.isdigit() else part.lower() for part in parts]

    # Sort labels with natural sorting by the DISPLAY name
    sorted_labels = sorted(historical_data.items(), key=lambda x: natural_sort_key(x[0]))

    # Add all sensors with data
    color_idx = 0
    for label, data_points in sorted_labels:
        if len(data_points) > 0:
            timestamps = [point[0] for point in data_points]
            values = [point[1] for point in data_points]

            # Get display label based on current toggle state
            display_label = get_display_label(label)

            fig.add_trace(go.Scatter(
                x=timestamps,
                y=values,
                name=display_label,
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
            title='Value',
            titlefont=dict(size=12),
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

        # Hover settings
        hovermode='x unified',
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

    # Update toggle button text
    toggle_button_text = 'Show Short Labels' if show_full_labels else 'Show Full Labels'

    return status, fig, toggle_button_text

# =============================================================================
# RUN
# =============================================================================

if __name__ == '__main__':
    print("="*70)
    print("LIVE TIME-SERIES DASHBOARD - FULL SCREEN")
    print("="*70)
    print(f"Open: http://localhost:8050")
    print(f"Refresh: {REFRESH_INTERVAL/1000/60:.0f} minutes | Filter: {TRACK_FILTER}")
    print("\nFirst poll happens immediately when you open the page!")
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
    print("\nNetwork Load:")
    print(f"  - Polling every {REFRESH_INTERVAL/1000/60:.0f} minutes = VERY SAFE for BMS")
    print("  - 1 API call per 5 min = minimal impact (~650 points per call)")
    print("  - Stores up to ~3.5 days of history")
    print("  - To reduce clutter: change TRACK_FILTER to 'pumps' or 'valves'")
    print("\nPress Ctrl+C to stop")
    print("="*70)

    app.run(debug=True, host='0.0.0.0', port=8050)
