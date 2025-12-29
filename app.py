from dash import Dash, html, dcc, page_container
import dash_bootstrap_components as dbc
from tension_data import (
    load_guitars, resolve_scales, resolve_string_types, note_to_freq,
    recommend_gauge
)

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], use_pages=True, pages_folder="pages", suppress_callback_exceptions=True)


def get_default_selections(guitars):
    """Generate default gauge/type selections for all guitars."""
    selections = {}
    for idx, guitar in enumerate(guitars):
        n_strings = guitar["n_strings"]
        scale = guitar["scale"]
        tuning = guitar["tuning"]
        string_types = guitar.get("string_types")
        target_plain = guitar.get("target_plain", [13.0, 15.5])
        target_wound = guitar.get("target_wound", [16.0, 20.0])
        
        scales = resolve_scales(scale, n_strings)
        types = resolve_string_types(string_types, n_strings)
        guitar_selections = []
        for i in range(n_strings):
            note = tuning[i] if i < len(tuning) else "E4"
            sc = scales[i]
            stype = types[i]
            freq = note_to_freq(note)
            target = target_plain if stype == "p" else target_wound
            gauge = recommend_gauge(stype, sc, freq, target)
            guitar_selections.append({"gauge": gauge, "type": stype})
        selections[str(idx)] = guitar_selections
    return selections


# Load guitars from file
_default_guitars = load_guitars()
_default_selections = get_default_selections(_default_guitars)

app.layout = dbc.Container([
    dcc.Store(id="guitars-store", data=_default_guitars, storage_type="memory"),
    dcc.Store(id="string-selections", data=_default_selections, storage_type="memory"),
    html.H1("🎸 String Tension Calculator", className="my-4 text-center"),
    dbc.Nav([
        dbc.NavLink("Summary", href="/", active="exact"),
        dbc.NavLink("Editor", href="/editor", active="exact"),
    ], pills=True, className="mb-4 justify-content-center"),
    page_container,
], fluid=True, style={"maxWidth": "900px"})


if __name__ == "__main__":
    app.run(debug=True)
