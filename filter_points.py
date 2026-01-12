"""
Point Filtering Interface - Blockers & Targets
Multi-stage wildcard filtering system for BMS points
"""

import dash
from dash import dcc, html, Input, Output, State, ALL, ctx
import dash_bootstrap_components as dbc
from datetime import datetime
from influxdb_client import InfluxDBClient
import fnmatch
import json

# =============================================================================
# CONFIGURATION
# =============================================================================

INFLUXDB_CONFIG = {
    'url': 'http://localhost:8086',
    'token': 'bms-super-secret-token-change-in-production',
    'org': 'birdlab',
    'bucket': 'bms_data'
}

influx_client = InfluxDBClient(
    url=INFLUXDB_CONFIG['url'],
    token=INFLUXDB_CONFIG['token'],
    org=INFLUXDB_CONFIG['org']
)

# =============================================================================
# DATA FETCHING
# =============================================================================

def fetch_all_points():
    """Fetch all unique point names from InfluxDB"""
    try:
        query_api = influx_client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_CONFIG['bucket']}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "bms_data")
          |> filter(fn: (r) => r.tenant_id == "sackville")
          |> distinct(column: "sensor_name")
          |> limit(n: 10000)
        '''

        result = query_api.query(query, org=INFLUXDB_CONFIG['org'])

        points = []
        for table in result:
            for record in table.records:
                sensor_name = record.values.get('sensor_name')
                if sensor_name:
                    points.append(sensor_name)

        return sorted(set(points))

    except Exception as e:
        print(f"Error fetching points: {e}")
        return []

# =============================================================================
# FILTERING LOGIC
# =============================================================================

def match_wildcard(point_name, pattern, invert=False):
    """
    Match point name against wildcard pattern.
    Supports * (any characters) and ? (single character)
    """
    if not pattern or pattern.strip() == '':
        return True  # Blank patterns are ignored

    # fnmatch for Unix-style wildcards
    matches = fnmatch.fnmatch(point_name, pattern)

    return not matches if invert else matches

def apply_blockers(points, blocker_rows):
    """
    Apply blocker filters (AND logic - all must pass).
    A point passes if it does NOT match the blocker (i.e., blockers REMOVE matching points).
    """
    filtered = points.copy()

    for blocker in blocker_rows:
        pattern = blocker.get('pattern', '').strip()
        invert = blocker.get('invert', False)

        if pattern:  # Only apply non-empty patterns
            # Remove points that match the blocker (keep points that DON'T match)
            filtered = [p for p in filtered if not match_wildcard(p, pattern, invert)]

    return filtered

def apply_targets(points, target_rows):
    """
    Apply target filters (OR logic - any must pass).
    A point passes if it matches ANY target.
    """
    if not target_rows or all(not t.get('pattern', '').strip() for t in target_rows):
        return points  # If no targets specified, pass everything

    matched = set()

    for target in target_rows:
        pattern = target.get('pattern', '').strip()
        invert = target.get('invert', False)

        if pattern:  # Only apply non-empty patterns
            for point in points:
                if match_wildcard(point, pattern, invert):
                    matched.add(point)

    return sorted(list(matched))

# =============================================================================
# APP SETUP
# =============================================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Point Filtering"

# Store for maintaining filter state
app.layout = dbc.Container([
    dcc.Store(id='blocker-counter', data=1),
    dcc.Store(id='target-counter', data=1),
    dcc.Store(id='all-points', data=[]),

    # Header
    dbc.Row([
        dbc.Col([
            html.H3("🔍 Point Filtering - Blockers & Targets", className="text-primary mb-0"),
            html.Small("Wildcard filtering with * (any) and ? (single char)", className="text-muted")
        ])
    ], className="mb-3 mt-3"),

    # Main content - 4 columns
    dbc.Row([
        # Column 1: Unfiltered Points
        dbc.Col([
            html.Div([
                html.H5([
                    "Unfiltered Points ",
                    html.Span(id='unfiltered-count', className="badge bg-info")
                ], className="text-center bg-secondary p-2 mb-0"),
                html.Div(id='unfiltered-list', className="point-list", style={
                    'height': '70vh',
                    'overflowY': 'auto',
                    'border': '1px solid #444',
                    'padding': '10px',
                    'fontSize': '11px',
                    'fontFamily': 'monospace'
                })
            ])
        ], width=3),

        # Column 2: Blockers (AND logic)
        dbc.Col([
            html.Div([
                html.H5([
                    "Blockers (AND) ",
                    html.Small("all must pass", className="text-muted")
                ], className="text-center bg-danger p-2 mb-2"),
                html.Div(id='blocker-rows', children=[]),
                dbc.Button("+ Add Blocker", id='add-blocker', color="danger", size="sm", className="w-100 mt-2")
            ])
        ], width=3),

        # Column 3: Targets (OR logic)
        dbc.Col([
            html.Div([
                html.H5([
                    "Targets (OR) ",
                    html.Small("any must pass", className="text-muted")
                ], className="text-center bg-success p-2 mb-2"),
                html.Div(id='target-rows', children=[]),
                dbc.Button("+ Add Target", id='add-target', color="success", size="sm", className="w-100 mt-2")
            ])
        ], width=3),

        # Column 4: Filtered Points
        dbc.Col([
            html.Div([
                html.H5([
                    "Filtered Points ",
                    html.Span(id='filtered-count', className="badge bg-info")
                ], className="text-center bg-secondary p-2 mb-0"),
                html.Div(id='filtered-list', className="point-list", style={
                    'height': '70vh',
                    'overflowY': 'auto',
                    'border': '1px solid #444',
                    'padding': '10px',
                    'fontSize': '11px',
                    'fontFamily': 'monospace'
                })
            ])
        ], width=3),
    ]),

    # Action buttons
    dbc.Row([
        dbc.Col([
            dbc.Button("🔄 Refresh Points", id='refresh-points', color="primary", className="me-2"),
            dbc.Button("🧹 Clear All Filters", id='clear-filters', color="warning", className="me-2"),
            dbc.Button("✅ Apply to Dashboard", id='apply-to-dashboard', color="success", className="me-2"),
            html.Span(id='apply-status', className="text-muted ms-3"),
            html.Span(id='last-update', className="text-muted ms-3")
        ], className="mt-3")
    ])

], fluid=True, style={'backgroundColor': '#222'})

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_filter_row(row_id, filter_type):
    """Create a single filter row with pattern input and invert checkbox"""
    return dbc.InputGroup([
        dbc.Input(
            id={'type': f'{filter_type}-pattern', 'index': row_id},
            placeholder="e.g., *Pump* or L11OS11D1*",
            size="sm",
            style={'fontFamily': 'monospace', 'fontSize': '11px'}
        ),
        dbc.InputGroupText([
            dbc.Checkbox(
                id={'type': f'{filter_type}-invert', 'index': row_id},
                className="me-1"
            ),
            html.Small("Invert", style={'fontSize': '10px'})
        ], style={'fontSize': '10px'}),
        dbc.Button(
            "×",
            id={'type': f'{filter_type}-remove', 'index': row_id},
            color="dark",
            size="sm",
            style={'fontSize': '14px'}
        )
    ], size="sm", className="mb-2")

# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    [Output('all-points', 'data'),
     Output('last-update', 'children')],
    [Input('refresh-points', 'n_clicks')],
    prevent_initial_call=False
)
def refresh_point_list(n):
    """Fetch all points from InfluxDB"""
    points = fetch_all_points()
    timestamp = datetime.now().strftime('%H:%M:%S')
    return points, f"Updated: {timestamp}"

@app.callback(
    [Output('unfiltered-list', 'children'),
     Output('unfiltered-count', 'children')],
    [Input('all-points', 'data')]
)
def display_unfiltered_points(points):
    """Display all unfiltered points"""
    if not points:
        return html.Div("No points found", className="text-muted"), "0"

    return [html.Div(point, className="mb-1") for point in points], str(len(points))

@app.callback(
    [Output('blocker-rows', 'children'),
     Output('blocker-counter', 'data')],
    [Input('add-blocker', 'n_clicks'),
     Input({'type': 'blocker-remove', 'index': ALL}, 'n_clicks')],
    [State('blocker-rows', 'children'),
     State('blocker-counter', 'data')],
    prevent_initial_call=True
)
def manage_blocker_rows(add_clicks, remove_clicks, current_rows, counter):
    """Add or remove blocker rows"""
    triggered_id = ctx.triggered_id

    if triggered_id == 'add-blocker':
        new_row = create_filter_row(counter, 'blocker')
        current_rows = current_rows or []
        return current_rows + [new_row], counter + 1

    elif isinstance(triggered_id, dict) and triggered_id.get('type') == 'blocker-remove':
        # Remove the clicked row
        index_to_remove = triggered_id['index']
        current_rows = [row for i, row in enumerate(current_rows)
                       if row['props']['children'][2]['props']['id']['index'] != index_to_remove]
        return current_rows, counter

    return current_rows or [create_filter_row(0, 'blocker')], counter

@app.callback(
    [Output('target-rows', 'children'),
     Output('target-counter', 'data')],
    [Input('add-target', 'n_clicks'),
     Input({'type': 'target-remove', 'index': ALL}, 'n_clicks')],
    [State('target-rows', 'children'),
     State('target-counter', 'data')],
    prevent_initial_call=True
)
def manage_target_rows(add_clicks, remove_clicks, current_rows, counter):
    """Add or remove target rows"""
    triggered_id = ctx.triggered_id

    if triggered_id == 'add-target':
        new_row = create_filter_row(counter, 'target')
        current_rows = current_rows or []
        return current_rows + [new_row], counter + 1

    elif isinstance(triggered_id, dict) and triggered_id.get('type') == 'target-remove':
        # Remove the clicked row
        index_to_remove = triggered_id['index']
        current_rows = [row for i, row in enumerate(current_rows)
                       if row['props']['children'][2]['props']['id']['index'] != index_to_remove]
        return current_rows, counter

    return current_rows or [create_filter_row(0, 'target')], counter

@app.callback(
    [Output('filtered-list', 'children'),
     Output('filtered-count', 'children')],
    [Input('all-points', 'data'),
     Input({'type': 'blocker-pattern', 'index': ALL}, 'value'),
     Input({'type': 'blocker-invert', 'index': ALL}, 'value'),
     Input({'type': 'target-pattern', 'index': ALL}, 'value'),
     Input({'type': 'target-invert', 'index': ALL}, 'value')]
)
def apply_filters(all_points, blocker_patterns, blocker_inverts, target_patterns, target_inverts):
    """Apply all filters and show results"""
    if not all_points:
        return html.Div("No points loaded", className="text-muted"), "0"

    # Build blocker list
    blockers = []
    for i, pattern in enumerate(blocker_patterns):
        invert = blocker_inverts[i] if i < len(blocker_inverts) else False
        blockers.append({'pattern': pattern or '', 'invert': bool(invert)})

    # Build target list
    targets = []
    for i, pattern in enumerate(target_patterns):
        invert = target_inverts[i] if i < len(target_inverts) else False
        targets.append({'pattern': pattern or '', 'invert': bool(invert)})

    # Apply filters
    filtered = apply_blockers(all_points, blockers)
    filtered = apply_targets(filtered, targets)

    if not filtered:
        return html.Div("No points match filters", className="text-warning"), "0"

    return [html.Div(point, className="mb-1") for point in filtered], str(len(filtered))

@app.callback(
    [Output('blocker-rows', 'children', allow_duplicate=True),
     Output('target-rows', 'children', allow_duplicate=True)],
    [Input('clear-filters', 'n_clicks')],
    prevent_initial_call=True
)
def clear_all_filters(n):
    """Clear all blocker and target filters"""
    return [create_filter_row(0, 'blocker')], [create_filter_row(0, 'target')]

@app.callback(
    Output('apply-status', 'children'),
    [Input('apply-to-dashboard', 'n_clicks')],
    [State('all-points', 'data'),
     State({'type': 'blocker-pattern', 'index': ALL}, 'value'),
     State({'type': 'blocker-invert', 'index': ALL}, 'value'),
     State({'type': 'target-pattern', 'index': ALL}, 'value'),
     State({'type': 'target-invert', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def apply_filters_to_dashboard(n_clicks, all_points, blocker_patterns, blocker_inverts, target_patterns, target_inverts):
    """Save filtered points to file for dashboard to read"""
    print(f"Apply callback triggered! n_clicks={n_clicks}")
    print(f"Points available: {len(all_points) if all_points else 0}")
    print(f"Blocker patterns: {blocker_patterns}")
    print(f"Target patterns: {target_patterns}")

    if not all_points:
        return "⚠️ No points loaded"

    # Build blocker list
    blockers = []
    for i, pattern in enumerate(blocker_patterns):
        invert = blocker_inverts[i] if i < len(blocker_inverts) else False
        blockers.append({'pattern': pattern or '', 'invert': bool(invert)})

    # Build target list
    targets = []
    for i, pattern in enumerate(target_patterns):
        invert = target_inverts[i] if i < len(target_inverts) else False
        targets.append({'pattern': pattern or '', 'invert': bool(invert)})

    print(f"Applying filters: {len(blockers)} blockers, {len(targets)} targets")

    # Apply filters
    filtered = apply_blockers(all_points, blockers)
    print(f"After blockers: {len(filtered)} points")
    filtered = apply_targets(filtered, targets)
    print(f"After targets: {len(filtered)} points")

    # Save to file
    filter_file = '/tmp/bms_filter_active.json'
    try:
        with open(filter_file, 'w') as f:
            json.dump({
                'points': filtered,
                'timestamp': datetime.now().isoformat(),
                'count': len(filtered)
            }, f)
        print(f"✅ Saved {len(filtered)} points to {filter_file}")
        return f"✅ Applied {len(filtered)} points to dashboard"
    except Exception as e:
        print(f"❌ Error saving filter: {e}")
        return f"❌ Error: {str(e)}"

# =============================================================================
# RUN
# =============================================================================

if __name__ == '__main__':
    print("="*70)
    print("POINT FILTERING INTERFACE")
    print("="*70)
    print(f"Open: http://localhost:8051")
    print("\nWildcard patterns:")
    print("  * = match any characters")
    print("  ? = match single character")
    print("\nLogic:")
    print("  Blockers: ALL must pass (AND)")
    print("  Targets: ANY must pass (OR)")
    print("  Invert: Reverse the match")
    print("="*70)

    app.run(debug=True, host='0.0.0.0', port=8051)
