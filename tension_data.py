import os
import yaml
from typing import List, Union, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Load string weight data from YAML
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def _load_string_weights():
    """Load string unit weights from YAML file."""
    filepath = os.path.join(DATA_DIR, 'string_weights.yaml')
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    # Convert string keys to float
    plain = {float(k): v for k, v in data['plain'].items()}
    wound = {float(k): v for k, v in data['wound'].items()}
    return plain, wound

PLAIN_UNIT_WEIGHTS, WOUND_UNIT_WEIGHTS = _load_string_weights()


PLAIN_GAUGES = sorted(PLAIN_UNIT_WEIGHTS.keys())
WOUND_GAUGES = sorted(WOUND_UNIT_WEIGHTS.keys())

A4 = 440.0

NOTE_INDEX = {
    "C": -9, "C#": -8, "D": -7, "D#": -6,
    "E": -5, "F": -4, "F#": -3,
    "G": -2, "G#": -1, "A": 0,
    "A#": 1, "B": 2,
}

FLAT_TO_SHARP = {
    "Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#",
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def note_to_freq(note: str) -> float:
    name = note[:-1]
    octave = int(note[-1])
    if name in FLAT_TO_SHARP:
        name = FLAT_TO_SHARP[name]
    semitones = NOTE_INDEX[name] + (octave - 4) * 12
    return A4 * (2 ** (semitones / 12))


def tension_from_mu(mu: float, scale: float, freq: float) -> float:
    return ((2 * scale * freq) ** 2 * mu) / 386.4


def resolve_scales(scale: Union[float, List[float]], n_strings: int) -> List[float]:
    if isinstance(scale, (int, float)):
        return [float(scale)] * n_strings
    if isinstance(scale, (list, tuple)) and len(scale) == 2:
        treble, bass = scale
        return [treble + (bass - treble) * i / (n_strings - 1) for i in range(n_strings)]
    raise ValueError("scale must be float or [treble, bass]")


def resolve_string_types(string_types: Optional[List[str]], n_strings: int) -> List[str]:
    if string_types is None:
        return ["p" if i < 3 else "w" for i in range(n_strings)]
    return string_types


def calc_tension(gauge: float, stype: str, scale: float, freq: float) -> float:
    table = PLAIN_UNIT_WEIGHTS if stype == "p" else WOUND_UNIT_WEIGHTS
    mu = table.get(gauge, 0)
    return tension_from_mu(mu, scale, freq)


def resolve_target(target) -> tuple:
    """Convert target to (min, max) tuple. Handles both single values and ranges."""
    if isinstance(target, (list, tuple)) and len(target) == 2:
        return (float(target[0]), float(target[1]))
    return (float(target), float(target))


def gauges_in_range(stype: str, scale: float, freq: float, target_range: tuple) -> list:
    """Return list of gauges that produce tension within target range."""
    table = PLAIN_UNIT_WEIGHTS if stype == "p" else WOUND_UNIT_WEIGHTS
    min_t, max_t = target_range
    valid = []
    for gauge, mu in table.items():
        tension = tension_from_mu(mu, scale, freq)
        if min_t <= tension <= max_t:
            valid.append(gauge)
    return sorted(valid)


def recommend_gauge(stype: str, scale: float, freq: float, target) -> float:
    """Recommend gauge closest to target midpoint that is IN RANGE. 
    Falls back to closest gauge if nothing is in range."""
    table = PLAIN_UNIT_WEIGHTS if stype == "p" else WOUND_UNIT_WEIGHTS
    min_t, max_t = resolve_target(target)
    midpoint = (min_t + max_t) / 2
    
    # First, find gauges that are in range
    in_range = []
    for gauge, mu in table.items():
        actual = tension_from_mu(mu, scale, freq)
        if min_t <= actual <= max_t:
            in_range.append((gauge, actual))
    
    # If we have in-range gauges, pick closest to midpoint
    if in_range:
        best_gauge = min(in_range, key=lambda x: abs(x[1] - midpoint))[0]
        return best_gauge
    
    # Fallback: no gauge in range, pick closest to midpoint anyway
    best_gauge, best_error = None, float("inf")
    for gauge, mu in table.items():
        actual = tension_from_mu(mu, scale, freq)
        error = abs(actual - midpoint)
        if error < best_error:
            best_gauge, best_error = gauge, error
    return best_gauge


def optimize_gauges(guitars_data: list, current_selections: dict = None) -> dict:
    """
    Optimize gauge selection to minimize unique gauges while staying in target ranges.
    If current_selections is provided, starts from those and consolidates singletons.
    Otherwise, uses greedy algorithm from scratch.
    Returns dict mapping (guitar_idx, string_idx) -> gauge
    """
    from collections import defaultdict
    
    # Build list of all string requirements
    strings = []  # [(guitar_idx, string_idx, stype, scale, freq, target_range), ...]
    
    for gidx, g in enumerate(guitars_data):
        n_strings = g["n_strings"]
        scale = g["scale"]
        tuning = g["tuning"]
        string_types = g.get("string_types")
        target_plain = g.get("target_plain", [13.0, 15.5])
        target_wound = g.get("target_wound", [16.0, 20.0])
        
        scales = resolve_scales(scale, n_strings)
        types = resolve_string_types(string_types, n_strings)
        
        for sidx in range(n_strings):
            note = tuning[sidx] if sidx < len(tuning) else "E4"
            stype = types[sidx]
            sc = scales[sidx]
            freq = note_to_freq(note)
            target = resolve_target(target_plain if stype == "p" else target_wound)
            
            strings.append((gidx, sidx, stype, sc, freq, target))
    
    # For each string, find valid gauges and compute midpoint error for tiebreaking
    string_options = []  # [(gidx, sidx, stype, scale, freq, target, valid_gauges)]
    for gidx, sidx, stype, scale, freq, target in strings:
        valid = gauges_in_range(stype, scale, freq, target)
        if not valid:
            # No gauge in range - find closest
            closest = recommend_gauge(stype, scale, freq, target)
            valid = [closest]
        string_options.append((gidx, sidx, stype, scale, freq, target, valid))
    
    # If we have current selections, start from those but fix out-of-range strings
    if current_selections:
        result = {}
        for gidx, sidx, stype, scale, freq, target, valid in string_options:
            key = (gidx, sidx)
            guitar_sel = current_selections.get(str(gidx), [])
            current_gauge = None
            if sidx < len(guitar_sel) and guitar_sel[sidx].get("gauge"):
                current_gauge = guitar_sel[sidx]["gauge"]
            
            if current_gauge is not None:
                # Check if current gauge is in range
                table = PLAIN_UNIT_WEIGHTS if stype == "p" else WOUND_UNIT_WEIGHTS
                mu = table.get(current_gauge, 0)
                tension = tension_from_mu(mu, scale, freq)
                min_t, max_t = target
                
                if min_t <= tension <= max_t:
                    # Current gauge is in range, keep it
                    result[key] = current_gauge
                else:
                    # Out of range - find a gauge that IS in range
                    # Use the valid gauges list we already computed
                    if valid:
                        # Pick gauge closest to midpoint from valid gauges
                        midpoint = (min_t + max_t) / 2
                        best_gauge = valid[0]
                        best_error = float("inf")
                        for g in valid:
                            mu_g = table.get(g, 0)
                            t = tension_from_mu(mu_g, scale, freq)
                            error = abs(t - midpoint)
                            if error < best_error:
                                best_gauge, best_error = g, error
                        result[key] = best_gauge
                    else:
                        # No gauge in range, use closest
                        result[key] = recommend_gauge(stype, scale, freq, target)
            else:
                # No current gauge, use valid gauge closest to midpoint
                if valid:
                    midpoint = (target[0] + target[1]) / 2
                    table = PLAIN_UNIT_WEIGHTS if stype == "p" else WOUND_UNIT_WEIGHTS
                    best_gauge = valid[0]
                    best_error = float("inf")
                    for g in valid:
                        mu_g = table.get(g, 0)
                        t = tension_from_mu(mu_g, scale, freq)
                        error = abs(t - midpoint)
                        if error < best_error:
                            best_gauge, best_error = g, error
                    result[key] = best_gauge
                else:
                    result[key] = recommend_gauge(stype, scale, freq, target)
    else:
        # Greedy optimization: prefer gauges that work for multiple strings
        # Count how many strings each gauge can satisfy
        gauge_counts = defaultdict(list)  # (gauge, stype) -> [(gidx, sidx), ...]
        for gidx, sidx, stype, scale, freq, target, valid in string_options:
            for g in valid:
                gauge_counts[(g, stype)].append((gidx, sidx))
        
        # Sort by most reusable gauges first
        sorted_gauges = sorted(gauge_counts.items(), key=lambda x: -len(x[1]))
        
        # Assign gauges greedily
        result = {}
        assigned = set()
        
        for (gauge, stype), string_list in sorted_gauges:
            for gidx, sidx in string_list:
                key = (gidx, sidx)
                if key not in assigned:
                    result[key] = gauge
                    assigned.add(key)
        
        # For any remaining unassigned, pick closest to midpoint
        for gidx, sidx, stype, scale, freq, target, valid in string_options:
            key = (gidx, sidx)
            if key not in result:
                # Pick gauge closest to midpoint
                midpoint = (target[0] + target[1]) / 2
                table = PLAIN_UNIT_WEIGHTS if stype == "p" else WOUND_UNIT_WEIGHTS
                best_gauge = valid[0]
                best_error = float("inf")
                for g in valid:
                    mu = table.get(g, 0)
                    tension = tension_from_mu(mu, scale, freq)
                    error = abs(tension - midpoint)
                    if error < best_error:
                        best_gauge, best_error = g, error
                result[key] = best_gauge
    
    # Second pass: for singletons (gauges used only once), try to switch to
    # a gauge that's already in use elsewhere, even if not as close to midpoint,
    # as long as it's still within the target range
    gauge_usage_count = defaultdict(int)
    for v in result.values():
        gauge_usage_count[v] += 1
    
    for gidx, sidx, stype, scale, freq, target, valid in string_options:
        key = (gidx, sidx)
        current = result[key]
        
        # Only optimize singletons (gauges used once)
        if gauge_usage_count[current] > 1:
            continue
        
        if len(valid) <= 1:
            continue
        
        # Find a valid gauge that's already used multiple times
        midpoint = (target[0] + target[1]) / 2
        table = PLAIN_UNIT_WEIGHTS if stype == "p" else WOUND_UNIT_WEIGHTS
        
        best_swap = None
        best_swap_error = float("inf")
        
        for g in valid:
            if g == current:
                continue
            # Prefer gauges already used elsewhere
            if gauge_usage_count[g] > 0:
                mu = table.get(g, 0)
                tension = tension_from_mu(mu, scale, freq)
                error = abs(tension - midpoint)
                if best_swap is None or error < best_swap_error:
                    best_swap = g
                    best_swap_error = error
        
        if best_swap is not None:
            # Switch to the shared gauge
            gauge_usage_count[current] -= 1
            gauge_usage_count[best_swap] += 1
            result[key] = best_swap
    
    return result


def load_guitars() -> list:
    """Load guitars from YAML file."""
    filepath = os.path.join(DATA_DIR, 'guitars.yaml')
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    return data.get('guitars', [])


def save_guitars(guitars: list) -> None:
    """Save guitars to YAML file."""
    filepath = os.path.join(DATA_DIR, 'guitars.yaml')
    
    # Build clean data structure
    data = {'guitars': []}
    for g in guitars:
        guitar = {
            'name': g['name'],
            'n_strings': g['n_strings'],
            'scale': g['scale'],
            'tuning': g['tuning'],
            'string_types': g.get('string_types'),
            'target_plain': g.get('target_plain', [13.0, 15.5]),
            'target_wound': g.get('target_wound', [16.0, 20.0]),
        }
        data['guitars'].append(guitar)
    
    with open(filepath, 'w') as f:
        f.write('# Guitar specifications - edited by the app\n')
        yaml.dump(data, f, default_flow_style=None, sort_keys=False, allow_unicode=True)
