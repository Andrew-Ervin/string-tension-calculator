"""
Flask API backend for String Tension Calculator
Provides REST endpoints for the React frontend
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from tension_data import (
    load_guitars, save_guitars, optimize_gauges,
    PLAIN_UNIT_WEIGHTS, WOUND_UNIT_WEIGHTS,
    PLAIN_GAUGES, WOUND_GAUGES,
    resolve_scales, resolve_string_types, note_to_freq,
    calc_tension, recommend_gauge
)

app = Flask(__name__)
CORS(app)  # Enable CORS for development


@app.route('/api/guitars', methods=['GET'])
def get_guitars():
    """Get all guitar specifications."""
    guitars = load_guitars()
    return jsonify(guitars)


@app.route('/api/guitars', methods=['PUT'])
def put_guitars():
    """Save guitar specifications."""
    guitars = request.json
    save_guitars(guitars)
    return jsonify({'status': 'ok'})


@app.route('/api/gauges', methods=['GET'])
def get_gauges():
    """Get available gauge options."""
    return jsonify({
        'plain': {
            'gauges': PLAIN_GAUGES,
            'weights': PLAIN_UNIT_WEIGHTS
        },
        'wound': {
            'gauges': WOUND_GAUGES,
            'weights': WOUND_UNIT_WEIGHTS
        }
    })


@app.route('/api/tension', methods=['POST'])
def calculate_tension():
    """Calculate tension for a string."""
    data = request.json
    gauge = data['gauge']
    stype = data['type']
    scale = data['scale']
    note = data['note']
    
    freq = note_to_freq(note)
    tension = calc_tension(gauge, stype, scale, freq)
    
    return jsonify({'tension': tension})


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """Optimize gauge selections to minimize unique gauges."""
    data = request.json
    guitars = data['guitars']
    selections = data['selections']
    
    # Run optimization
    result = optimize_gauges(guitars, selections)
    
    # Convert result format from {(gidx, sidx): gauge} to {gidx: [{gauge, type}]}
    output = {}
    for (gidx, sidx), gauge in result.items():
        gidx_str = str(gidx)
        if gidx_str not in output:
            output[gidx_str] = [None] * guitars[gidx]['n_strings']
        
        # Get the string type - preserve from current selections if available
        guitar = guitars[gidx]
        current_sel = selections.get(gidx_str, [])
        if sidx < len(current_sel) and current_sel[sidx] and current_sel[sidx].get('type'):
            stype = current_sel[sidx]['type']
        else:
            types = resolve_string_types(guitar.get('string_types'), guitar['n_strings'])
            stype = types[sidx]
        
        output[gidx_str][sidx] = {'gauge': gauge, 'type': stype}
    
    return jsonify(output)


@app.route('/api/recommend', methods=['POST'])
def recommend():
    """Recommend gauge for a string based on target tension."""
    data = request.json
    stype = data['type']
    scale = data['scale']
    note = data['note']
    target = data['target']
    
    freq = note_to_freq(note)
    gauge = recommend_gauge(stype, scale, freq, target)
    tension = calc_tension(gauge, stype, scale, freq)
    
    return jsonify({
        'gauge': gauge,
        'tension': tension
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001)
