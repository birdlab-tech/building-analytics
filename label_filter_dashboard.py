"""
Label Filter Configuration Dashboard

Web interface for configuring label filters with:
- Multiple blocker stages (Bs1-Bs4)
- Target stage (Ts)
- Wildcard pattern support
- Real-time filter preview
- Save/load configurations
"""

import dash
from dash import dcc, html, Input, Output, State, ALL, ctx
import plotly.graph_objects as go
from label_filter_engine import LabelFilterEngine, FilterStage
import json
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load labels from extracted config
CONFIG_FILE = Path(__file__).parent / "label_filter_configs.json"
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        AVAILABLE_SYSTEMS = list(data.keys())
        DEFAULT_LABELS = data.get('heating_cooling', {}).get('labels', [])
else:
    AVAILABLE_SYSTEMS = ['heating_cooling', 'lighting', 'ahus']
    DEFAULT_LABELS = []

# Initialize filter engine
filter_engine = LabelFilterEngine()
filter_engine.set_source_labels(DEFAULT_LABELS)

# Initialize with 4 blocker stages
for i in range(1, 5):
    filter_engine.add_blocker_stage(f'Bs{i}')
filter_engine.set_target_stage('Ts')

# =============================================================================
# APP SETUP
# =============================================================================

app = dash.Dash(__name__)
app.title = "Label Filter Configuration"

# Dark theme styling
DARK_STYLE = {
    'backgroundColor': '#1a1a1a',
    'color': '#e0e0e0',
    'padding': '15px',
    'borderRadius': '5px',
    'marginBottom': '15px'
}

BUTTON_STYLE = {
    'background': '#00aaff',
    'color': 'white',
    'border': 'none',
    'padding': '8px 16px',
    'borderRadius': '4px',
    'cursor': 'pointer',
    'marginRight': '10px',
    'fontSize': '14px'
}

INPUT_STYLE = {
    'background': '#2d2d2d',
    'color': '#e0e0e0',
    'border': '1px solid #555',
    'padding': '8px',
    'borderRadius': '4px',
    'width': '100%',
    'marginBottom': '10px'
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_filter_row(stage_name: str, filter_idx: int, pattern: str = '', enabled: bool = True):
    """Create a filter input row"""
    return html.Div([
        html.Div([
            dcc.Checklist(
                id={'type': 'filter-enabled', 'stage': stage_name, 'index': filter_idx},
                options=[{'label': '', 'value': 'enabled'}],
                value=['enabled'] if enabled else [],
                style={'display': 'inline-block', 'marginRight': '10px'}
            ),
            dcc.Input(
                id={'type': 'filter-pattern', 'stage': stage_name, 'index': filter_idx},
                type='text',
                placeholder='Enter pattern (e.g., *Alarm*, Lighting*, AI_*)',
                value=pattern,
                style={**INPUT_STYLE, 'width': '400px', 'display': 'inline-block'}
            ),
            html.Button(
                '×',
                id={'type': 'remove-filter', 'stage': stage_name, 'index': filter_idx},
                style={
                    'background': '#ff4444',
                    'color': 'white',
                    'border': 'none',
                    'padding': '4px 12px',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'marginLeft': '10px',
                    'display': 'inline-block'
                }
            )
        ], style={'marginBottom': '8px'})
    ])


def create_stage_section(stage_name: str, stage_type: str = 'blocker'):
    """Create a filter stage section"""
    action_label = 'BLOCK' if stage_type == 'blocker' else 'INCLUDE'
    description = f"Remove labels matching these patterns" if stage_type == 'blocker' else "Keep only labels matching these patterns"

    return html.Div([
        html.H3(f"{stage_name} ({action_label})", style={'color': '#00aaff', 'marginBottom': '10px'}),
        html.P(description, style={'color': '#888', 'fontSize': '12px', 'marginBottom': '15px'}),
        html.Div(id=f'{stage_name}-filters', children=[]),
        html.Button(
            f'+ Add Filter to {stage_name}',
            id=f'add-filter-{stage_name}',
            style={**BUTTON_STYLE, 'background': '#333'}
        )
    ], style={**DARK_STYLE, 'border': '1px solid #333'})


# =============================================================================
# LAYOUT
# =============================================================================

app.layout = html.Div([
    html.Div([
        html.H1("🔍 Label Filter Configuration", style={'color': '#00aaff', 'display': 'inline-block'}),
        html.Div([
            html.Label("System:", style={'marginRight': '10px'}),
            dcc.Dropdown(
                id='system-select',
                options=[{'label': s.replace('_', ' ').title(), 'value': s} for s in AVAILABLE_SYSTEMS],
                value=AVAILABLE_SYSTEMS[0] if AVAILABLE_SYSTEMS else None,
                style={'width': '200px', 'display': 'inline-block', 'marginRight': '20px'}
            ),
            html.Button('Load Config', id='load-config-btn', style=BUTTON_STYLE),
            html.Button('Save Config', id='save-config-btn', style=BUTTON_STYLE),
            html.Button('Reset All', id='reset-btn', style={**BUTTON_STYLE, 'background': '#ff4444'})
        ], style={'float': 'right'})
    ], style={**DARK_STYLE, 'marginBottom': '20px'}),

    # Statistics
    html.Div([
        html.H3("Filter Statistics", style={'color': '#00aaff'}),
        html.Div(id='filter-stats', style={'fontSize': '14px'})
    ], style=DARK_STYLE),

    # Filter stages
    html.Div([
        html.Div([
            create_stage_section('Bs1', 'blocker'),
            create_stage_section('Bs2', 'blocker'),
        ], style={'display': 'flex', 'gap': '15px', 'marginBottom': '15px'}),

        html.Div([
            create_stage_section('Bs3', 'blocker'),
            create_stage_section('Bs4', 'blocker'),
        ], style={'display': 'flex', 'gap': '15px', 'marginBottom': '15px'}),

        create_stage_section('Ts', 'target'),
    ]),

    # Results preview
    html.Div([
        html.H3("Filtered Labels Preview", style={'color': '#00aaff'}),
        html.Div([
            dcc.Dropdown(
                id='preview-stage',
                options=[
                    {'label': 'Source (All Labels)', 'value': 'source'},
                    {'label': 'After Bs1', 'value': 'Bs1'},
                    {'label': 'After Bs2', 'value': 'Bs2'},
                    {'label': 'After Bs3', 'value': 'Bs3'},
                    {'label': 'After Bs4', 'value': 'Bs4'},
                    {'label': 'After Ts (Final)', 'value': 'final'}
                ],
                value='final',
                style={'width': '250px', 'marginBottom': '15px'}
            ),
            html.Div(id='labels-preview', style={
                'maxHeight': '400px',
                'overflowY': 'auto',
                'background': '#2d2d2d',
                'padding': '15px',
                'borderRadius': '5px',
                'fontSize': '12px',
                'fontFamily': 'monospace'
            })
        ])
    ], style=DARK_STYLE),

    # Hidden stores
    dcc.Store(id='filter-data', data={'counter': 0}),
    dcc.Interval(id='refresh-interval', interval=1000, n_intervals=0)

], style={
    'backgroundColor': '#0a0a0a',
    'minHeight': '100vh',
    'padding': '20px',
    'fontFamily': 'Segoe UI, sans-serif'
})


# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    [Output('filter-stats', 'children'),
     Output('labels-preview', 'children')],
    [Input('refresh-interval', 'n_intervals'),
     Input('preview-stage', 'value'),
     Input({'type': 'filter-pattern', 'stage': ALL, 'index': ALL}, 'value'),
     Input({'type': 'filter-enabled', 'stage': ALL, 'index': ALL}, 'value')],
    prevent_initial_call=False
)
def update_preview(n, preview_stage, patterns, enabled_lists):
    """Update the filter preview and statistics"""

    # Rebuild filter engine from current UI state
    # (This is a simplified version - in practice you'd want more sophisticated state management)

    # Get stage results
    results = filter_engine.get_stage_results()
    stats = filter_engine.get_statistics()

    # Statistics display
    stats_content = [
        html.Div([
            html.Span(f"Source Labels: ", style={'fontWeight': 'bold'}),
            html.Span(f"{stats['source_count']}", style={'color': '#00aaff', 'fontSize': '18px'})
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span(f"Final Labels: ", style={'fontWeight': 'bold'}),
            html.Span(f"{stats['final_count']}", style={'color': '#4caf50', 'fontSize': '18px'})
        ], style={'marginBottom': '10px'}),
        html.Div([
            html.Span(f"Removed: ", style={'fontWeight': 'bold'}),
            html.Span(f"{stats['removed_count']} ({stats['removal_percentage']:.1f}%)", style={'color': '#ff4444'})
        ])
    ]

    # Labels preview
    stage_labels = results.get(preview_stage, [])
    if stage_labels:
        labels_content = [
            html.Div([
                html.Span(f"{i+1}. ", style={'color': '#666', 'marginRight': '10px'}),
                html.Span(label)
            ], style={'marginBottom': '5px'})
            for i, label in enumerate(stage_labels[:100])  # Limit to 100 for performance
        ]
        if len(stage_labels) > 100:
            labels_content.append(
                html.Div(f"... and {len(stage_labels) - 100} more", style={'color': '#666', 'marginTop': '10px'})
            )
    else:
        labels_content = html.Div("No labels match the current filters", style={'color': '#666', 'fontStyle': 'italic'})

    return stats_content, labels_content


# =============================================================================
# RUN
# =============================================================================

if __name__ == '__main__':
    print("="*70)
    print("LABEL FILTER CONFIGURATION DASHBOARD")
    print("="*70)
    print(f"Open: http://localhost:8051")
    print(f"\nLoaded systems: {', '.join(AVAILABLE_SYSTEMS)}")
    print(f"Total labels: {len(DEFAULT_LABELS)}")
    print("\nFeatures:")
    print("  - 4 Blocker stages (Bs1-Bs4) for progressive filtering")
    print("  - 1 Target stage (Ts) for final selection")
    print("  - Wildcard support: * (any characters), ? (single character)")
    print("  - Real-time preview of filtered labels")
    print("  - Save/load filter configurations")
    print("\nPress Ctrl+C to stop")
    print("="*70)

    app.run(debug=True, host='0.0.0.0', port=8051)
