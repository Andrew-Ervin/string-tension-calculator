from dash import html, dcc, callback, Output, Input, State, register_page
import dash_bootstrap_components as dbc
from collections import Counter, defaultdict
from tension_data import (
    GUITARS, GuitarSpec, format_gauge, resolve_scales, resolve_string_types, 
    note_to_freq, recommend_gauge, tuning_name, load_guitars, dict_to_guitar,
    calc_tension, resolve_target, PLAIN_UNIT_WEIGHTS, WOUND_UNIT_WEIGHTS
)

register_page(__name__, path="/", name="Summary")


def get_default_selections(guitars=None):
    """Generate default gauge/type selections for all guitars."""
    if guitars is None:
        guitars = [dict_to_guitar(g) for g in load_guitars()]
    else:
        guitars = [dict_to_guitar(g) if isinstance(g, dict) else g for g in guitars]
    
    selections = {}
    for idx, guitar in enumerate(guitars):
        scales = resolve_scales(guitar.scale, guitar.n_strings)
        types = resolve_string_types(guitar.string_types, guitar.n_strings)
        guitar_selections = []
        for i in range(guitar.n_strings):
            note = guitar.tuning[i] if i < len(guitar.tuning) else "E4"
            scale = scales[i]
            stype = types[i]
            freq = note_to_freq(note)
            target = guitar.target_plain if stype == "p" else guitar.target_wound
            gauge = recommend_gauge(stype, scale, freq, target)
            guitar_selections.append({"gauge": gauge, "type": stype})
        selections[str(idx)] = guitar_selections
    return selections


def build_guitar_table(selections, guitars=None):
    """Build the guitar × string table from selections."""
    if guitars is None:
        guitars = [dict_to_guitar(g) for g in load_guitars()]
    else:
        guitars = [dict_to_guitar(g) if isinstance(g, dict) else g for g in guitars]
    
    if not guitars:
        return html.P("No guitars defined.", className="text-muted")
    
    max_strings = max(g.n_strings for g in guitars)
    
    header = html.Tr(
        [html.Th("Guitar", style={"textAlign": "left"}), html.Th("Tuning", style={"textAlign": "center"})] +
        [html.Th(str(i + 1), style={"textAlign": "center", "width": "50px"}) for i in range(max_strings)]
    )
    
    rows = []
    for idx, guitar in enumerate(guitars):
        guitar_sel = selections.get(str(idx), [])
        cells = [
            html.Td(guitar.name, style={"textAlign": "left", "whiteSpace": "nowrap"}),
            html.Td(tuning_name(guitar.tuning), style={"textAlign": "center", "color": "#888", "fontSize": "0.85rem"}),
        ]
        
        for i in range(max_strings):
            if i < len(guitar_sel) and guitar_sel[i].get("gauge"):
                gauge = guitar_sel[i]["gauge"]
                stype = guitar_sel[i]["type"]
                cells.append(html.Td(
                    format_gauge(gauge),
                    style={"textAlign": "center", "color": "#adb5bd" if stype == "p" else "#00bc8c"}
                ))
            else:
                cells.append(html.Td("", style={"textAlign": "center"}))
        rows.append(html.Tr(cells))
    
    return html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
        className="table table-sm"
    )


def build_gauge_count_table(selections, guitars=None):
    """Build the gauge count table from selections with swap analysis for singletons."""
    if guitars is None:
        guitars = [dict_to_guitar(g) for g in load_guitars()]
    else:
        guitars = [dict_to_guitar(g) if isinstance(g, dict) else g for g in guitars]
    
    # Build a lookup for guitar targets by index
    guitar_targets = {}
    for idx, guitar in enumerate(guitars):
        plain_target = resolve_target(guitar.target_plain)
        wound_target = resolve_target(guitar.target_wound)
        guitar_targets[idx] = {
            "p": plain_target,
            "w": wound_target,
        }
    
    # Collect all gauge usages with string info for swap analysis
    gauge_usages = defaultdict(list)  # (gauge, stype) -> [usage_info]
    
    for idx, guitar in enumerate(guitars):
        guitar_sel = selections.get(str(idx), [])
        scales = resolve_scales(guitar.scale, guitar.n_strings)
        
        for i, s in enumerate(guitar_sel):
            if s.get("gauge") and s.get("type"):
                gauge = s["gauge"]
                stype = s["type"]
                scale = scales[i] if i < len(scales) else scales[-1]
                note = guitar.tuning[i] if i < len(guitar.tuning) else "E4"
                freq = note_to_freq(note)
                
                gauge_usages[(gauge, stype)].append({
                    "guitar_idx": idx,
                    "guitar": guitar.name,
                    "string": i + 1,
                    "scale": scale,
                    "freq": freq,
                    "stype": stype,
                })
    
    if not gauge_usages:
        return html.P("No data", className="text-muted")
    
    # Get counts and find common gauges (count > 1)
    counter = {k: len(v) for k, v in gauge_usages.items()}
    common_gauges = {k for k, count in counter.items() if count > 1}
    
    sorted_gauges = sorted(gauge_usages.items(), key=lambda x: x[0][0])
    
    rows = []
    for (gauge, stype), usages in sorted_gauges:
        count = len(usages)
        swap_info = ""
        
        # For singletons, calculate best swap option
        if count == 1 and common_gauges:
            usage = usages[0]
            guitar_idx = usage["guitar_idx"]
            scale = usage["scale"]
            freq = usage["freq"]
            
            # Get target for THIS guitar and THIS string type
            target_min, target_max = guitar_targets[guitar_idx][stype]
            midpoint = (target_min + target_max) / 2
            
            # Find best swap among common gauges of same type
            same_type_common = [(g, st) for (g, st) in common_gauges if st == stype]
            
            if same_type_common:
                best_swap = None
                best_violation = float("inf")
                best_tension = None
                
                for (swap_gauge, _) in same_type_common:
                    swap_tension = calc_tension(swap_gauge, stype, scale, freq)
                    
                    # Calculate violation (how far outside range, or 0 if in range)
                    if swap_tension < target_min:
                        violation = target_min - swap_tension
                    elif swap_tension > target_max:
                        violation = swap_tension - target_max
                    else:
                        violation = 0
                    
                    # Tiebreak by distance from midpoint
                    distance = abs(swap_tension - midpoint)
                    
                    if violation < best_violation or (violation == best_violation and distance < abs(best_tension - midpoint if best_tension else float("inf"))):
                        best_swap = swap_gauge
                        best_violation = violation
                        best_tension = swap_tension
                
                if best_swap is not None:
                    if best_violation > 0:
                        # Show violation amount
                        swap_info = f"→{format_gauge(best_swap)}: {best_tension:.1f}lb (±{best_violation:.1f})"
                    else:
                        # In range
                        swap_info = f"→{format_gauge(best_swap)}: {best_tension:.1f}lb ✓"
        
        row_cells = [
            html.Td(format_gauge(gauge), style={"textAlign": "center", "color": "#adb5bd" if stype == "p" else "#00bc8c"}),
            html.Td(stype, style={"textAlign": "center"}),
            html.Td(str(count), style={"textAlign": "right"}),
        ]
        
        if swap_info:
            color = "#f39c12" if "±" in swap_info else "#00bc8c"
            row_cells.append(html.Td(swap_info, style={"textAlign": "left", "fontSize": "0.85rem", "color": color}))
        else:
            row_cells.append(html.Td("", style={"textAlign": "left"}))
        
        rows.append(html.Tr(row_cells))
    
    return html.Table(
        [
            html.Thead(html.Tr([
                html.Th("Gauge", style={"textAlign": "center"}),
                html.Th("Type", style={"textAlign": "center"}),
                html.Th("Count", style={"textAlign": "right"}),
                html.Th("Swap Option", style={"textAlign": "left"}),
            ])),
            html.Tbody(rows)
        ],
        style={"width": "100%", "borderCollapse": "collapse"},
        className="table table-sm"
    )


# Pre-compute defaults for initial render
_defaults = get_default_selections()

layout = html.Div([
    dcc.Location(id="summary-url", refresh=False),
    html.P("Gauges by guitar and string position. Plain strings in gray, wound in green.", 
           className="text-muted text-center mb-4"),
    
    dbc.Card([
        dbc.CardHeader(html.H5("Gauges by Guitar", className="mb-0")),
        dbc.CardBody(build_guitar_table(_defaults), id="guitar-table-container"),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Gauge Inventory", className="mb-0")),
                dbc.CardBody(build_gauge_count_table(_defaults), id="gauge-count-container"),
            ]),
        ], md=6),
    ], justify="center"),
])


@callback(
    Output("guitar-table-container", "children"),
    Output("gauge-count-container", "children"),
    Input("summary-url", "pathname"),
    Input("string-selections", "data"),
    Input("guitars-store", "data"),
)
def update_summary(pathname, selections, guitars_data):
    """Update summary tables when selections or guitars change."""
    # Use loaded defaults if stores are empty
    if not guitars_data:
        guitars_data = load_guitars()
    if not selections:
        selections = get_default_selections(guitars_data)
    return build_guitar_table(selections, guitars_data), build_gauge_count_table(selections, guitars_data)
