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
import os

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

# Directory for saved configurations
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'filter_configs')
os.makedirs(CONFIG_DIR, exist_ok=True)

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

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    url_base_pathname='/filter/'
)
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
    ]),

    # Save/Load Configuration
    dbc.Row([
        dbc.Col([
            html.Hr(className="my-4"),
            html.H5("💾 Save/Load Filter Configurations", className="mb-3"),

            dbc.Row([
                # Save section
                dbc.Col([
                    html.Label("Save Current Filters:", className="mb-2"),
                    dbc.InputGroup([
                        dbc.Input(id='config-name', placeholder="e.g., pumps-only", size="sm"),
                        dbc.Button("💾 Save", id='save-config', color="info", size="sm")
                    ], className="mb-2"),
                    html.Small(id='save-status', className="text-muted")
                ], width=6),

                # Load section
                dbc.Col([
                    html.Label("Saved Configurations:", className="mb-2"),
                    html.Div(id='saved-configs-list', className="mb-2"),
                    dbc.Button("🔄 Refresh List", id='refresh-configs', color="secondary", size="sm", outline=True)
                ], width=6)
            ])
        ])
    ], className="mt-3")

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

    # Only proceed if something was actually clicked
    if not triggered_id:
        raise dash.exceptions.PreventUpdate

    # Prevent this callback from firing when remove buttons are created (from load_config)
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'blocker-remove':
        # Check if this was a real click (n_clicks > 0) vs just component creation (n_clicks = None/0)
        idx = triggered_id['index']
        if idx < len(remove_clicks):
            if not remove_clicks[idx] or remove_clicks[idx] == 0:
                raise dash.exceptions.PreventUpdate

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

    # If we get here, something unexpected triggered this callback
    raise dash.exceptions.PreventUpdate

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

    # Only proceed if something was actually clicked
    if not triggered_id:
        raise dash.exceptions.PreventUpdate

    # Prevent this callback from firing when remove buttons are created (from load_config)
    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'target-remove':
        # Check if this was a real click (n_clicks > 0) vs just component creation (n_clicks = None/0)
        idx = triggered_id['index']
        if idx < len(remove_clicks):
            if not remove_clicks[idx] or remove_clicks[idx] == 0:
                raise dash.exceptions.PreventUpdate

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

    # If we get here, something unexpected triggered this callback
    raise dash.exceptions.PreventUpdate

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
     Output('target-rows', 'children', allow_duplicate=True),
     Output('blocker-counter', 'data', allow_duplicate=True),
     Output('target-counter', 'data', allow_duplicate=True)],
    [Input('clear-filters', 'n_clicks')],
    prevent_initial_call=True
)
def clear_all_filters(n):
    """Clear all blocker and target filters"""
    return [create_filter_row(0, 'blocker')], [create_filter_row(0, 'target')], 1, 1

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
        return f"✅ Applied {len(filtered)} points to dashboard (click Refresh on dashboard to see changes)"
    except Exception as e:
        print(f"❌ Error saving filter: {e}")
        return f"❌ Error: {str(e)}"

@app.callback(
    Output('save-status', 'children'),
    [Input('save-config', 'n_clicks')],
    [State('config-name', 'value'),
     State({'type': 'blocker-pattern', 'index': ALL}, 'value'),
     State({'type': 'blocker-invert', 'index': ALL}, 'value'),
     State({'type': 'target-pattern', 'index': ALL}, 'value'),
     State({'type': 'target-invert', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def save_configuration(n_clicks, config_name, blocker_patterns, blocker_inverts, target_patterns, target_inverts):
    """Save current filter configuration to file"""
    if not config_name or not config_name.strip():
        return "❌ Please enter a configuration name"

    # Sanitize filename
    safe_name = "".join(c for c in config_name if c.isalnum() or c in ('-', '_')).strip()
    if not safe_name:
        return "❌ Invalid configuration name"

    # Build config
    config = {
        'name': config_name,
        'blockers': [],
        'targets': [],
        'created': datetime.now().isoformat()
    }

    for i, pattern in enumerate(blocker_patterns):
        if pattern and pattern.strip():
            invert = blocker_inverts[i] if i < len(blocker_inverts) else False
            config['blockers'].append({'pattern': pattern, 'invert': bool(invert)})

    for i, pattern in enumerate(target_patterns):
        if pattern and pattern.strip():
            invert = target_inverts[i] if i < len(target_inverts) else False
            config['targets'].append({'pattern': pattern, 'invert': bool(invert)})

    # Save to file
    config_file = os.path.join(CONFIG_DIR, f'{safe_name}.json')
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        return f"✅ Saved as '{safe_name}'"
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.callback(
    Output('saved-configs-list', 'children'),
    [Input('refresh-configs', 'n_clicks'),
     Input('save-config', 'n_clicks')],
    prevent_initial_call=False
)
def list_saved_configs(refresh_clicks, save_clicks):
    """List all saved configurations"""
    try:
        configs = []
        for filename in sorted(os.listdir(CONFIG_DIR)):
            if filename.endswith('.json'):
                config_path = os.path.join(CONFIG_DIR, filename)
                try:
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)

                    config_name = filename[:-5]  # Remove .json
                    num_blockers = len(config_data.get('blockers', []))
                    num_targets = len(config_data.get('targets', []))

                    configs.append(
                        dbc.ButtonGroup([
                            dbc.Button(
                                f"📁 {config_name}",
                                id={'type': 'load-config', 'index': config_name},
                                color="light",
                                size="sm",
                                outline=True,
                                className="text-start"
                            ),
                            dbc.Button(
                                "🗑️",
                                id={'type': 'delete-config', 'index': config_name},
                                color="danger",
                                size="sm",
                                outline=True
                            )
                        ], className="mb-1 w-100")
                    )
                except:
                    continue

        if not configs:
            return html.Small("No saved configurations", className="text-muted")

        return html.Div(configs)

    except Exception as e:
        return html.Small(f"Error loading configs: {e}", className="text-danger")

@app.callback(
    [Output('blocker-rows', 'children', allow_duplicate=True),
     Output('target-rows', 'children', allow_duplicate=True),
     Output('blocker-counter', 'data', allow_duplicate=True),
     Output('target-counter', 'data', allow_duplicate=True),
     Output('save-status', 'children', allow_duplicate=True)],
    [Input({'type': 'load-config', 'index': ALL}, 'n_clicks')],
    [State({'type': 'load-config', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def load_configuration(n_clicks, ids):
    """Load a saved configuration"""
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate

    # Find which button was clicked
    triggered = ctx.triggered_id
    if not triggered:
        raise dash.exceptions.PreventUpdate

    config_name = triggered['index']
    config_file = os.path.join(CONFIG_DIR, f'{config_name}.json')

    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)

        print(f"Loading config '{config_name}':")
        print(f"  Blockers: {config_data.get('blockers', [])}")
        print(f"  Targets: {config_data.get('targets', [])}")

        # Rebuild blocker rows
        blocker_rows = []
        for i, blocker in enumerate(config_data.get('blockers', [])):
            row = dbc.InputGroup([
                dbc.Input(
                    id={'type': 'blocker-pattern', 'index': i},
                    placeholder="e.g., *Pump*",
                    value=blocker['pattern'],
                    size="sm",
                    style={'fontFamily': 'monospace', 'fontSize': '11px'}
                ),
                dbc.InputGroupText([
                    dbc.Checkbox(
                        id={'type': 'blocker-invert', 'index': i},
                        value=blocker['invert'],
                        className="me-1"
                    ),
                    html.Small("Invert", style={'fontSize': '10px'})
                ], style={'fontSize': '10px'}),
                dbc.Button(
                    "×",
                    id={'type': 'blocker-remove', 'index': i},
                    color="dark",
                    size="sm",
                    style={'fontSize': '14px'}
                )
            ], size="sm", className="mb-2")
            blocker_rows.append(row)

        if not blocker_rows:
            blocker_rows = [create_filter_row(0, 'blocker')]

        # Rebuild target rows
        target_rows = []
        for i, target in enumerate(config_data.get('targets', [])):
            row = dbc.InputGroup([
                dbc.Input(
                    id={'type': 'target-pattern', 'index': i},
                    placeholder="e.g., *Pump*",
                    value=target['pattern'],
                    size="sm",
                    style={'fontFamily': 'monospace', 'fontSize': '11px'}
                ),
                dbc.InputGroupText([
                    dbc.Checkbox(
                        id={'type': 'target-invert', 'index': i},
                        value=target['invert'],
                        className="me-1"
                    ),
                    html.Small("Invert", style={'fontSize': '10px'})
                ], style={'fontSize': '10px'}),
                dbc.Button(
                    "×",
                    id={'type': 'target-remove', 'index': i},
                    color="dark",
                    size="sm",
                    style={'fontSize': '14px'}
                )
            ], size="sm", className="mb-2")
            target_rows.append(row)

        if not target_rows:
            target_rows = [create_filter_row(0, 'target')]

        # Update counters to next available index
        blocker_counter = len(blocker_rows)
        target_counter = len(target_rows)

        print(f"  Created {len(blocker_rows)} blocker rows, {len(target_rows)} target rows")

        return blocker_rows, target_rows, blocker_counter, target_counter, f"✅ Loaded '{config_name}'"

    except Exception as e:
        print(f"Error loading config: {e}")
        import traceback
        traceback.print_exc()
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, f"❌ Error loading: {str(e)}"

@app.callback(
    [Output('saved-configs-list', 'children', allow_duplicate=True),
     Output('save-status', 'children', allow_duplicate=True)],
    [Input({'type': 'delete-config', 'index': ALL}, 'n_clicks')],
    [State({'type': 'delete-config', 'index': ALL}, 'id')],
    prevent_initial_call=True
)
def delete_configuration(n_clicks, ids):
    """Delete a saved configuration"""
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate

    # Find which button was clicked
    triggered = ctx.triggered_id
    if not triggered:
        raise dash.exceptions.PreventUpdate

    config_name = triggered['index']
    config_file = os.path.join(CONFIG_DIR, f'{config_name}.json')

    try:
        os.remove(config_file)
        # Refresh the list
        configs = []
        for filename in sorted(os.listdir(CONFIG_DIR)):
            if filename.endswith('.json'):
                config_path = os.path.join(CONFIG_DIR, filename)
                try:
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)

                    name = filename[:-5]

                    configs.append(
                        dbc.ButtonGroup([
                            dbc.Button(
                                f"📁 {name}",
                                id={'type': 'load-config', 'index': name},
                                color="light",
                                size="sm",
                                outline=True,
                                className="text-start"
                            ),
                            dbc.Button(
                                "🗑️",
                                id={'type': 'delete-config', 'index': name},
                                color="danger",
                                size="sm",
                                outline=True
                            )
                        ], className="mb-1 w-100")
                    )
                except:
                    continue

        if not configs:
            configs = html.Small("No saved configurations", className="text-muted")
        else:
            configs = html.Div(configs)

        return configs, f"✅ Deleted '{config_name}'"

    except Exception as e:
        return dash.no_update, f"❌ Error deleting: {str(e)}"

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

    app.run(debug=False, host='0.0.0.0', port=8051)
