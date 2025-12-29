from dash import html, dcc, callback, Output, Input, State, ALL, MATCH, register_page, ctx, no_update
import dash_bootstrap_components as dbc
import json
from tension_data import (
    PLAIN_GAUGES, WOUND_GAUGES, GuitarSpec, load_guitars, save_guitars,
    resolve_scales, resolve_string_types, note_to_freq, resolve_target,
    recommend_gauge, calc_tension, format_gauge, tuning_name, optimize_gauges
)

register_page(__name__, path="/editor", name="Editor")


def dict_to_guitar(d):
    """Convert dict back to GuitarSpec."""
    return GuitarSpec(
        name=d["name"],
        n_strings=d["n_strings"],
        scale=d["scale"],
        tuning=d["tuning"],
        string_types=d.get("string_types"),
        target_plain=d.get("target_plain", [13.0, 15.5]),
        target_wound=d.get("target_wound", [16.0, 20.0]),
    )


def build_guitar_card(guitar_dict, idx):
    """Build a card for one guitar with editable properties."""
    guitar = dict_to_guitar(guitar_dict)
    scales = resolve_scales(guitar.scale, guitar.n_strings)
    types = resolve_string_types(guitar.string_types, guitar.n_strings)
    
    # Get target ranges
    tp_min, tp_max = resolve_target(guitar.target_plain)
    tw_min, tw_max = resolve_target(guitar.target_wound)
    
    # Build string rows
    rows = []
    for i in range(guitar.n_strings):
        note = guitar.tuning[i] if i < len(guitar.tuning) else "E4"
        scale = scales[i]
        stype = types[i]
        freq = note_to_freq(note)
        target = guitar.target_plain if stype == "p" else guitar.target_wound
        rec_gauge = recommend_gauge(stype, scale, freq, target)
        gauge_options = PLAIN_GAUGES if stype == "p" else WOUND_GAUGES
        
        row = html.Tr([
            html.Td(str(i + 1), style={"textAlign": "center", "width": "40px"}),
            html.Td(
                dbc.Input(
                    id={"type": "note-input", "guitar": idx, "string": i},
                    value=note,
                    size="sm",
                    style={"width": "60px", "textAlign": "center"},
                ),
                style={"width": "80px"}
            ),
            html.Td(
                dcc.Dropdown(
                    id={"type": "gauge", "guitar": idx, "string": i},
                    options=[{"label": format_gauge(g), "value": g} for g in gauge_options],
                    value=rec_gauge,
                    clearable=False,
                    style={"width": "90px", "color": "#000"},
                ),
                style={"width": "110px"}
            ),
            html.Td(
                dcc.Dropdown(
                    id={"type": "stype", "guitar": idx, "string": i},
                    options=[
                        {"label": "p", "value": "p"},
                        {"label": "w", "value": "w"},
                    ],
                    value=stype,
                    clearable=False,
                    style={"width": "60px", "color": "#000"},
                ),
                style={"width": "80px"}
            ),
            html.Td(
                html.Span("", id={"type": "tension", "guitar": idx, "string": i}),
                style={"textAlign": "right", "width": "80px"}
            ),
        ])
        rows.append(row)
    
    table = html.Table(
        [
            html.Thead(html.Tr([
                html.Th("#", style={"textAlign": "center"}),
                html.Th("Note"),
                html.Th("Gauge"),
                html.Th("Type"),
                html.Th("Tension", style={"textAlign": "right"}),
            ])),
            html.Tbody(rows),
        ],
        style={"width": "100%", "borderCollapse": "collapse"},
    )
    
    # Scale inputs
    if isinstance(guitar.scale, list):
        scale_inputs = dbc.Row([
            dbc.Col([
                dbc.Label("Treble Scale", size="sm"),
                dbc.Input(
                    id={"type": "scale-treble", "guitar": idx},
                    type="number", value=guitar.scale[0], size="sm", step=0.25
                ),
            ], width=6),
            dbc.Col([
                dbc.Label("Bass Scale", size="sm"),
                dbc.Input(
                    id={"type": "scale-bass", "guitar": idx},
                    type="number", value=guitar.scale[1], size="sm", step=0.25
                ),
            ], width=6),
        ], className="mb-2")
    else:
        scale_inputs = dbc.Row([
            dbc.Col([
                dbc.Label("Scale Length", size="sm"),
                dbc.Input(
                    id={"type": "scale-treble", "guitar": idx},
                    type="number", value=guitar.scale, size="sm", step=0.25
                ),
            ], width=6),
            dbc.Col([
                dbc.Label("(Bass - multiscale)", size="sm"),
                dbc.Input(
                    id={"type": "scale-bass", "guitar": idx},
                    type="number", value="", size="sm", step=0.25, placeholder="optional"
                ),
            ], width=6),
        ], className="mb-2")
    
    # Target tension range inputs
    target_inputs = dbc.Row([
        dbc.Col([
            dbc.Label("Plain Target", size="sm"),
            dbc.InputGroup([
                dbc.Input(id={"type": "target-plain-min", "guitar": idx}, type="number", 
                         value=tp_min, size="sm", step=0.5, style={"width": "60px"}),
                dbc.InputGroupText("-", style={"padding": "0 4px"}),
                dbc.Input(id={"type": "target-plain-max", "guitar": idx}, type="number", 
                         value=tp_max, size="sm", step=0.5, style={"width": "60px"}),
            ], size="sm"),
        ], width=6),
        dbc.Col([
            dbc.Label("Wound Target", size="sm"),
            dbc.InputGroup([
                dbc.Input(id={"type": "target-wound-min", "guitar": idx}, type="number", 
                         value=tw_min, size="sm", step=0.5, style={"width": "60px"}),
                dbc.InputGroupText("-", style={"padding": "0 4px"}),
                dbc.Input(id={"type": "target-wound-max", "guitar": idx}, type="number", 
                         value=tw_max, size="sm", step=0.5, style={"width": "60px"}),
            ], size="sm"),
        ], width=6),
    ], className="mb-2")
    
    # Store scale and freq data for callbacks
    string_data = [
        {"scale": scales[i], "freq": note_to_freq(guitar.tuning[i]) if i < len(guitar.tuning) else 329.63}
        for i in range(guitar.n_strings)
    ]
    
    return dbc.Card([
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    dbc.Input(
                        id={"type": "guitar-name", "guitar": idx},
                        value=guitar.name,
                        size="sm",
                        style={"fontWeight": "bold"},
                    ),
                ], width=4),
                dbc.Col([
                    html.Span(tuning_name(guitar.tuning), className="text-muted",
                             id={"type": "tuning-name", "guitar": idx}),
                ], width=2, className="text-center"),
                dbc.Col([
                    dbc.InputGroup([
                        dbc.InputGroupText("Strings:", style={"fontSize": "0.85rem"}),
                        dbc.Input(
                            id={"type": "n-strings", "guitar": idx},
                            type="number", value=guitar.n_strings,
                            min=4, max=12, size="sm", style={"width": "60px"}
                        ),
                    ], size="sm"),
                ], width=4),
                dbc.Col([
                    dbc.Button("✕", id={"type": "delete-guitar", "guitar": idx}, 
                              color="danger", size="sm", outline=True),
                ], width=2, className="text-end"),
            ], align="center"),
        ]),
        dbc.CardBody([
            scale_inputs,
            target_inputs,
            dcc.Store(id={"type": "data", "guitar": idx}, data=string_data),
            table
        ]),
    ], className="mb-4", id={"type": "guitar-card", "guitar": idx})


def build_all_cards(guitars_data):
    """Build all guitar cards from guitars data."""
    if not guitars_data:
        return []
    return [build_guitar_card(g, i) for i, g in enumerate(guitars_data)]


# Initial layout - guitars rendered via callback
layout = html.Div([
    html.P("Edit guitar properties and adjust string gauges. Use Optimize to minimize unique gauges.", 
           className="text-muted text-center mb-3"),
    
    # Global target range controls
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Global Plain Target", className="mb-1"),
                    dbc.InputGroup([
                        dbc.Input(id="global-plain-min", type="number", value=13.0, 
                                 size="sm", step=0.5, style={"width": "70px"}),
                        dbc.InputGroupText("-", style={"padding": "0 6px"}),
                        dbc.Input(id="global-plain-max", type="number", value=15.5, 
                                 size="sm", step=0.5, style={"width": "70px"}),
                        dbc.InputGroupText("lb"),
                    ], size="sm"),
                ], width=4),
                dbc.Col([
                    dbc.Label("Global Wound Target", className="mb-1"),
                    dbc.InputGroup([
                        dbc.Input(id="global-wound-min", type="number", value=16.0, 
                                 size="sm", step=0.5, style={"width": "70px"}),
                        dbc.InputGroupText("-", style={"padding": "0 6px"}),
                        dbc.Input(id="global-wound-max", type="number", value=20.0, 
                                 size="sm", step=0.5, style={"width": "70px"}),
                        dbc.InputGroupText("lb"),
                    ], size="sm"),
                ], width=4),
                dbc.Col([
                    dbc.Label("\u00A0", className="mb-1"),  # spacer
                    html.Div([
                        dbc.Button("Apply to All", id="apply-global-targets-btn", 
                                  color="info", size="sm", className="w-100"),
                    ]),
                ], width=4),
            ], align="end"),
        ], className="py-2"),
    ], className="mb-3"),
    
    dbc.Row([
        dbc.Col(dbc.Button("+ Add Guitar", id="add-guitar-btn", color="success"), width="auto"),
        dbc.Col(dbc.Button("⚡ Optimize Gauges", id="optimize-btn", color="warning"), width="auto"),
        dbc.Col(dbc.Button("💾 Save to File", id="save-guitars-btn", color="primary"), width="auto"),
        dbc.Col(html.Span("", id="save-status", className="text-success"), width="auto", className="align-self-center"),
    ], className="mb-4 g-2"),
    dcc.Store(id="optimized-gauges", data=None),
    html.Div(id="guitars-container"),
])


# ─────────────────────────────────────────────────────────────────────────────
# Callbacks
# ─────────────────────────────────────────────────────────────────────────────

@callback(
    Output("guitars-container", "children"),
    Input("guitars-store", "data"),
)
def render_guitars(guitars_data):
    """Render guitar cards from store."""
    if not guitars_data:
        return html.P("No guitars defined. Click 'Add Guitar' to create one.", 
                     className="text-muted text-center")
    return build_all_cards(guitars_data)


@callback(
    Output("guitars-store", "data", allow_duplicate=True),
    Output("save-status", "children", allow_duplicate=True),
    Input("apply-global-targets-btn", "n_clicks"),
    State("global-plain-min", "value"),
    State("global-plain-max", "value"),
    State("global-wound-min", "value"),
    State("global-wound-max", "value"),
    State("guitars-store", "data"),
    prevent_initial_call=True,
)
def apply_global_targets(n_clicks, p_min, p_max, w_min, w_max, guitars_data):
    """Apply global target ranges to all guitars."""
    if not n_clicks or not guitars_data:
        return no_update, no_update
    
    p_min = float(p_min) if p_min is not None else 13.0
    p_max = float(p_max) if p_max is not None else 15.5
    w_min = float(w_min) if w_min is not None else 16.0
    w_max = float(w_max) if w_max is not None else 20.0
    
    updated = []
    for g in guitars_data:
        new_g = dict(g)
        new_g["target_plain"] = [p_min, p_max]
        new_g["target_wound"] = [w_min, w_max]
        updated.append(new_g)
    
    return updated, f"✓ Applied to {len(updated)} guitars"


@callback(
    Output("guitars-store", "data", allow_duplicate=True),
    Input("add-guitar-btn", "n_clicks"),
    State("global-plain-min", "value"),
    State("global-plain-max", "value"),
    State("global-wound-min", "value"),
    State("global-wound-max", "value"),
    State("guitars-store", "data"),
    prevent_initial_call=True,
)
def add_guitar(n_clicks, p_min, p_max, w_min, w_max, guitars_data):
    """Add a new default guitar using global targets."""
    if not n_clicks:
        return no_update
    
    p_min = float(p_min) if p_min is not None else 13.0
    p_max = float(p_max) if p_max is not None else 15.5
    w_min = float(w_min) if w_min is not None else 16.0
    w_max = float(w_max) if w_max is not None else 20.0
    
    guitars_data = guitars_data or []
    new_guitar = {
        "name": f"New Guitar {len(guitars_data) + 1}",
        "n_strings": 6,
        "scale": 25.5,
        "tuning": ["E4", "B3", "G3", "D3", "A2", "E2"],
        "string_types": None,
        "target_plain": [p_min, p_max],
        "target_wound": [w_min, w_max],
    }
    return guitars_data + [new_guitar]


@callback(
    Output("guitars-store", "data", allow_duplicate=True),
    Input({"type": "delete-guitar", "guitar": ALL}, "n_clicks"),
    State("guitars-store", "data"),
    prevent_initial_call=True,
)
def delete_guitar(n_clicks, guitars_data):
    """Delete a guitar by index."""
    if not any(n_clicks):
        return no_update
    # Find which button was clicked
    triggered = ctx.triggered_id
    if triggered and "guitar" in triggered:
        idx = triggered["guitar"]
        if guitars_data and 0 <= idx < len(guitars_data):
            return guitars_data[:idx] + guitars_data[idx+1:]
    return no_update


@callback(
    Output("guitars-store", "data", allow_duplicate=True),
    Input({"type": "guitar-name", "guitar": ALL}, "value"),
    Input({"type": "n-strings", "guitar": ALL}, "value"),
    Input({"type": "scale-treble", "guitar": ALL}, "value"),
    Input({"type": "scale-bass", "guitar": ALL}, "value"),
    Input({"type": "target-plain-min", "guitar": ALL}, "value"),
    Input({"type": "target-plain-max", "guitar": ALL}, "value"),
    Input({"type": "target-wound-min", "guitar": ALL}, "value"),
    Input({"type": "target-wound-max", "guitar": ALL}, "value"),
    Input({"type": "note-input", "guitar": ALL, "string": ALL}, "value"),
    State("guitars-store", "data"),
    prevent_initial_call=True,
)
def update_guitar_specs(names, n_strings_list, treble_scales, bass_scales, 
                        tp_mins, tp_maxs, tw_mins, tw_maxs, all_notes, guitars_data):
    """Update guitar specs when inputs change."""
    if not guitars_data or not names:
        return no_update
    
    updated = []
    note_idx = 0
    
    for idx, g in enumerate(guitars_data):
        if idx >= len(names):
            updated.append(g)
            continue
            
        new_g = dict(g)
        new_g["name"] = names[idx] if names[idx] else g["name"]
        
        # Handle n_strings change
        new_n = n_strings_list[idx] if idx < len(n_strings_list) and n_strings_list[idx] else g["n_strings"]
        new_n = max(4, min(12, int(new_n)))
        
        # Collect notes for this guitar
        old_n = g["n_strings"]
        guitar_notes = []
        for i in range(old_n):
            if note_idx < len(all_notes):
                guitar_notes.append(all_notes[note_idx] or "E4")
                note_idx += 1
        
        # Adjust tuning if string count changed
        if new_n != old_n:
            if new_n > old_n:
                guitar_notes.extend(["B1"] * (new_n - old_n))
            else:
                guitar_notes = guitar_notes[:new_n]
        
        new_g["n_strings"] = new_n
        new_g["tuning"] = guitar_notes
        
        # Handle scale
        treble = treble_scales[idx] if idx < len(treble_scales) else None
        bass = bass_scales[idx] if idx < len(bass_scales) else None
        
        if treble and bass:
            new_g["scale"] = [float(treble), float(bass)]
        elif treble:
            new_g["scale"] = float(treble)
        
        # Handle target ranges
        tp_min = tp_mins[idx] if idx < len(tp_mins) and tp_mins[idx] is not None else 13.0
        tp_max = tp_maxs[idx] if idx < len(tp_maxs) and tp_maxs[idx] is not None else 15.5
        tw_min = tw_mins[idx] if idx < len(tw_mins) and tw_mins[idx] is not None else 16.0
        tw_max = tw_maxs[idx] if idx < len(tw_maxs) and tw_maxs[idx] is not None else 20.0
        
        new_g["target_plain"] = [float(tp_min), float(tp_max)]
        new_g["target_wound"] = [float(tw_min), float(tw_max)]
        
        updated.append(new_g)
    
    return updated


@callback(
    Output({"type": "gauge", "guitar": ALL, "string": ALL}, "options"),
    Input({"type": "stype", "guitar": ALL, "string": ALL}, "value"),
    prevent_initial_call=True,
)
def update_gauge_options(stypes):
    """Update gauge dropdown options when type changes."""
    if not stypes:
        return no_update
    return [
        [{"label": format_gauge(g), "value": g} for g in (PLAIN_GAUGES if st == "p" else WOUND_GAUGES)]
        for st in stypes
    ]


@callback(
    Output({"type": "tension", "guitar": ALL, "string": ALL}, "children"),
    Output("string-selections", "data"),
    Input({"type": "gauge", "guitar": ALL, "string": ALL}, "value"),
    Input({"type": "stype", "guitar": ALL, "string": ALL}, "value"),
    Input({"type": "note-input", "guitar": ALL, "string": ALL}, "value"),
    State({"type": "scale-treble", "guitar": ALL}, "value"),
    State({"type": "scale-bass", "guitar": ALL}, "value"),
    State({"type": "n-strings", "guitar": ALL}, "value"),
    State("guitars-store", "data"),
    State("string-selections", "data"),
)
def update_tensions_and_store(gauges, stypes, notes, treble_scales, bass_scales, n_strings_list, guitars_data, current_selections):
    """Recalculate tensions and save to store."""
    # Don't update store if inputs are empty/None - preserve existing store data
    if not gauges or not stypes or not guitars_data:
        # For pattern-matching ALL outputs, need to return list of no_updates
        return [no_update] * len(gauges) if gauges else [], no_update
    
    # Also check if all gauges are None (can happen during dropdown updates)
    if all(g is None for g in gauges):
        # Return no_update for each tension output, and preserve existing selections
        return [no_update] * len(gauges), current_selections if current_selections else no_update
    
    results = []
    new_selections = {}
    
    string_idx = 0
    for idx, g in enumerate(guitars_data):
        n_strings = n_strings_list[idx] if idx < len(n_strings_list) and n_strings_list[idx] else g["n_strings"]
        n_strings = int(n_strings)
        
        # Get target ranges for this guitar
        target_plain = g.get("target_plain", [13.0, 15.5])
        target_wound = g.get("target_wound", [16.0, 20.0])
        plain_min, plain_max = target_plain[0], target_plain[1]
        wound_min, wound_max = target_wound[0], target_wound[1]
        
        # Get scale
        treble = treble_scales[idx] if idx < len(treble_scales) and treble_scales[idx] else 25.5
        bass = bass_scales[idx] if idx < len(bass_scales) and bass_scales[idx] else None
        scale = [float(treble), float(bass)] if bass else float(treble)
        scales = resolve_scales(scale, n_strings)
        
        guitar_sel = []
        for i in range(n_strings):
            if string_idx >= len(gauges):
                break
            gauge = gauges[string_idx]
            stype = stypes[string_idx] if string_idx < len(stypes) else "p"
            note = notes[string_idx] if string_idx < len(notes) else "E4"
            sc = scales[i] if i < len(scales) else scales[-1]
            
            try:
                freq = note_to_freq(note)
            except:
                freq = 329.63  # E4 default
            
            if gauge is not None and stype is not None:
                tension = calc_tension(gauge, stype, sc, freq)
                
                # Check if tension is in range
                if stype == "p":
                    in_range = plain_min <= tension <= plain_max
                else:
                    in_range = wound_min <= tension <= wound_max
                
                # Color: green if in range, red/orange if out
                if in_range:
                    color = "#00bc8c"  # green
                else:
                    color = "#e74c3c"  # red
                
                results.append(html.Span(f"{tension:.1f}", style={"color": color}))
                guitar_sel.append({"gauge": gauge, "type": stype})
            else:
                results.append("")
                guitar_sel.append({"gauge": None, "type": None})
            
            string_idx += 1
        
        new_selections[str(idx)] = guitar_sel
    
    return results, new_selections


@callback(
    Output("save-status", "children"),
    Input("save-guitars-btn", "n_clicks"),
    State("guitars-store", "data"),
    prevent_initial_call=True,
)
def save_to_file(n_clicks, guitars_data):
    """Save guitars to guitar_specs.py file."""
    if not n_clicks or not guitars_data:
        return no_update
    try:
        save_guitars(guitars_data)
        return "✓ Saved!"
    except Exception as e:
        return f"Error: {str(e)}"


@callback(
    Output("optimized-gauges", "data"),
    Output("string-selections", "data", allow_duplicate=True),
    Output("save-status", "children", allow_duplicate=True),
    Input("optimize-btn", "n_clicks"),
    State("guitars-store", "data"),
    State("string-selections", "data"),
    prevent_initial_call=True,
)
def run_optimization(n_clicks, guitars_data, current_selections):
    """Run gauge optimization and store results."""
    if not n_clicks or not guitars_data:
        return no_update, no_update, no_update
    
    try:
        # Pass current selections so optimizer starts from them
        optimized = optimize_gauges(guitars_data, current_selections)
        # Convert tuple keys to strings for JSON serialization
        result = {f"{k[0]},{k[1]}": v for k, v in optimized.items()}
        
        # Also build the string-selections format directly
        new_selections = {}
        for (gidx, sidx), gauge in optimized.items():
            if str(gidx) not in new_selections:
                new_selections[str(gidx)] = []
            # Ensure list is long enough
            while len(new_selections[str(gidx)]) <= sidx:
                new_selections[str(gidx)].append({"gauge": None, "type": None})
        
        # Now fill in the gauges with types
        for gidx, g in enumerate(guitars_data):
            n_strings = g["n_strings"]
            string_types = g.get("string_types")
            types = resolve_string_types(string_types, n_strings)
            
            if str(gidx) not in new_selections:
                new_selections[str(gidx)] = []
            
            for sidx in range(n_strings):
                key = (gidx, sidx)
                if key in optimized:
                    gauge = optimized[key]
                    stype = types[sidx]
                    while len(new_selections[str(gidx)]) <= sidx:
                        new_selections[str(gidx)].append({"gauge": None, "type": None})
                    new_selections[str(gidx)][sidx] = {"gauge": gauge, "type": stype}
        
        # Count unique gauges
        unique = len(set(optimized.values()))
        return result, new_selections, f"⚡ Optimized: {unique} unique gauges"
    except Exception as e:
        return no_update, no_update, f"Error: {str(e)}"


@callback(
    Output({"type": "gauge", "guitar": ALL, "string": ALL}, "value"),
    Input("optimized-gauges", "data"),
    State({"type": "gauge", "guitar": ALL, "string": ALL}, "id"),
    prevent_initial_call=True,
)
def apply_optimized_gauges(optimized_data, gauge_ids):
    """Apply optimized gauge selections to dropdowns."""
    if not optimized_data or not gauge_ids:
        return no_update
    
    results = []
    for gid in gauge_ids:
        key = f"{gid['guitar']},{gid['string']}"
        if key in optimized_data:
            results.append(optimized_data[key])
        else:
            results.append(no_update)
    
    return results
