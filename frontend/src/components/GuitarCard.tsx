// Guitar card component for editing a single guitar
import { useApp } from '../context/AppContext';
import type { Guitar, StringSelection } from '../types';
import { PLAIN_GAUGES, WOUND_GAUGES } from '../constants';
import {
  resolveScales,
  resolveStringTypes,
  noteToFreq,
  calcTension,
  formatGauge,
  isInRange,
  recommendGauge,
} from '../utils/tension';
import './GuitarCard.css';

interface GuitarCardProps {
  guitar: Guitar;
  index: number;
  selections: StringSelection[];
  expanded: boolean;
  onToggle: () => void;
  onDelete: () => void;
  singletonGauges?: Set<string>;
}

export function GuitarCard({
  guitar,
  index,
  selections,
  expanded,
  onToggle,
  onDelete,
  singletonGauges,
}: GuitarCardProps) {
  const { dispatch } = useApp();
  const scales = resolveScales(guitar.scale, guitar.n_strings);
  const types = resolveStringTypes(guitar.string_types, guitar.n_strings);

  const getGuitarColor = (index: number) => {
    const guitarColors = [
      '#FFB3BA', // light red
      '#FFDFBA', // light orange
      '#FFFFBA', // light yellow
      '#BAFFBA', // light green
      '#BAE1FF', // light blue
      '#D4BAFF', // light purple
      '#FFBAE1', // light pink
      '#BAFFD4', // light mint
      '#FFD4BA', // light peach
      '#E1BAFF', // light lavender
    ];
    return guitarColors[index % guitarColors.length];
  };

  const updateGuitar = (updates: Partial<Guitar>) => {
    dispatch({
      type: 'UPDATE_GUITAR',
      payload: { index, guitar: { ...guitar, ...updates } },
    });
  };

  const updateStringSelection = (stringIdx: number, selection: StringSelection) => {
    dispatch({
      type: 'UPDATE_STRING_SELECTION',
      payload: { guitarIdx: index, stringIdx, selection },
    });
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateGuitar({ name: e.target.value });
  };

  const handleScaleChange = (value: number, isBass: boolean) => {
    if (Array.isArray(guitar.scale)) {
      const newScale: [number, number] = isBass 
        ? [guitar.scale[0], value]
        : [value, guitar.scale[1]];
      updateGuitar({ scale: newScale });
    } else {
      if (isBass && value) {
        updateGuitar({ scale: [guitar.scale, value] });
      } else {
        updateGuitar({ scale: value });
      }
    }
  };

  const handleNStringsChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newNStrings = parseInt(e.target.value, 10);
    const currentTuning = guitar.tuning;
    
    // Standard tunings for different string counts
    const standardTunings: Record<number, string[]> = {
      4: ['G3', 'D3', 'A2', 'E2'],
      5: ['G3', 'D3', 'A2', 'E2', 'B1'],
      6: ['E4', 'B3', 'G3', 'D3', 'A2', 'E2'],
      7: ['E4', 'B3', 'G3', 'D3', 'A2', 'E2', 'B1'],
      8: ['E4', 'B3', 'G3', 'D3', 'A2', 'E2', 'B1', 'F#1'],
    };

    let newTuning: string[];
    if (newNStrings < currentTuning.length) {
      newTuning = currentTuning.slice(0, newNStrings);
    } else if (newNStrings > currentTuning.length) {
      newTuning = [...currentTuning];
      const standard = standardTunings[newNStrings] || standardTunings[6];
      while (newTuning.length < newNStrings) {
        newTuning.push(standard[newTuning.length] || 'E2');
      }
    } else {
      newTuning = currentTuning;
    }

    updateGuitar({ n_strings: newNStrings, tuning: newTuning });

    // Update selections for new strings
    const newScales = resolveScales(guitar.scale, newNStrings);
    const newTypes = resolveStringTypes(guitar.string_types, newNStrings);
    for (let i = selections.length; i < newNStrings; i++) {
      const note = newTuning[i] || 'E4';
      const scale = newScales[i];
      const stype = newTypes[i];
      const freq = noteToFreq(note);
      const target = stype === 'p' ? guitar.target_plain : guitar.target_wound;
      const gauge = recommendGauge(stype, scale, freq, target);
      updateStringSelection(i, { gauge, type: stype });
    }
  };

  const handleNoteChange = (stringIdx: number, note: string) => {
    const newTuning = [...guitar.tuning];
    newTuning[stringIdx] = note;
    updateGuitar({ tuning: newTuning });
  };

  const handleGaugeChange = (stringIdx: number, gauge: number) => {
    const currentType = selections[stringIdx]?.type || types[stringIdx];
    updateStringSelection(stringIdx, { gauge, type: currentType });
  };

  const handleTypeChange = (stringIdx: number, type: 'p' | 'w') => {
    // Recommend new gauge for the new type
    const note = guitar.tuning[stringIdx] || 'E4';
    const scale = scales[stringIdx];
    const freq = noteToFreq(note);
    const target = type === 'p' ? guitar.target_plain : guitar.target_wound;
    const newGauge = recommendGauge(type, scale, freq, target);
    updateStringSelection(stringIdx, { gauge: newGauge, type });
  };

  const handleTargetChange = (
    kind: 'plain' | 'wound',
    minOrMax: 'min' | 'max',
    value: number
  ) => {
    if (kind === 'plain') {
      const newTarget: [number, number] = [...guitar.target_plain];
      newTarget[minOrMax === 'min' ? 0 : 1] = value;
      updateGuitar({ target_plain: newTarget });
    } else {
      const newTarget: [number, number] = [...guitar.target_wound];
      newTarget[minOrMax === 'min' ? 0 : 1] = value;
      updateGuitar({ target_wound: newTarget });
    }
  };

  // Calculate total tension
  const totalTension = selections.reduce((sum, sel, i) => {
    if (!sel?.gauge) return sum;
    const note = guitar.tuning[i] || 'E4';
    const scale = scales[i];
    const freq = noteToFreq(note);
    return sum + calcTension(sel.gauge, sel.type, scale, freq);
  }, 0);

  return (
    <div className={`guitar-card ${expanded ? 'expanded' : ''}`} style={{ borderLeft: `4px solid ${getGuitarColor(index)}` }}>
      <div className="guitar-header" onClick={onToggle}>
        <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
        <span className="guitar-title">{guitar.name}</span>
        <span className="guitar-meta">
          {guitar.n_strings} strings · {totalTension.toFixed(1)} lb total
        </span>
        <button
          className="delete-btn"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Delete guitar"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>

      {expanded && (
        <div className="guitar-body">
          <div className="guitar-settings">
            <div className="settings-row">
              <div className="setting-group">
                <label>Name</label>
                <input
                  type="text"
                  value={guitar.name}
                  onChange={handleNameChange}
                  className="input"
                />
              </div>

              <div className="setting-group">
                <label>Strings</label>
                <select
                  value={guitar.n_strings}
                  onChange={handleNStringsChange}
                  className="select"
                >
                  {[4, 5, 6, 7, 8, 9, 10, 11, 12].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </div>

              <div className="setting-group">
                <label>Scale (treble)</label>
                <input
                  type="number"
                  value={Array.isArray(guitar.scale) ? guitar.scale[0] : guitar.scale}
                  onChange={(e) => handleScaleChange(parseFloat(e.target.value), false)}
                  step={0.25}
                  className="input input-sm"
                />
              </div>

              <div className="setting-group">
                <label>Scale (bass)</label>
                <input
                  type="number"
                  value={Array.isArray(guitar.scale) ? guitar.scale[1] : ''}
                  onChange={(e) => handleScaleChange(parseFloat(e.target.value), true)}
                  step={0.25}
                  placeholder="multiscale"
                  className="input input-sm"
                />
              </div>
            </div>

            <div className="settings-row targets-row">
              <div className="setting-group">
                <label>Plain target</label>
                <div className="range-inputs">
                  <input
                    type="number"
                    value={guitar.target_plain[0]}
                    onChange={(e) => handleTargetChange('plain', 'min', parseFloat(e.target.value))}
                    step={0.5}
                    className="input input-xs"
                  />
                  <span>-</span>
                  <input
                    type="number"
                    value={guitar.target_plain[1]}
                    onChange={(e) => handleTargetChange('plain', 'max', parseFloat(e.target.value))}
                    step={0.5}
                    className="input input-xs"
                  />
                </div>
              </div>

              <div className="setting-group">
                <label>Wound target</label>
                <div className="range-inputs">
                  <input
                    type="number"
                    value={guitar.target_wound[0]}
                    onChange={(e) => handleTargetChange('wound', 'min', parseFloat(e.target.value))}
                    step={0.5}
                    className="input input-xs"
                  />
                  <span>-</span>
                  <input
                    type="number"
                    value={guitar.target_wound[1]}
                    onChange={(e) => handleTargetChange('wound', 'max', parseFloat(e.target.value))}
                    step={0.5}
                    className="input input-xs"
                  />
                </div>
              </div>
            </div>
          </div>

          <table className="string-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Note</th>
                <th>Gauge</th>
                <th>Type</th>
                <th className="text-right">Tension</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: guitar.n_strings }, (_, i) => {
                const sel = selections[i] || { gauge: 0.01, type: types[i] };
                const note = guitar.tuning[i] || 'E4';
                const scale = scales[i];
                const freq = noteToFreq(note);
                const tension = calcTension(sel.gauge, sel.type, scale, freq);
                const target = sel.type === 'p' ? guitar.target_plain : guitar.target_wound;
                const inRange = isInRange(tension, target);
                const gaugeOptions = sel.type === 'p' ? PLAIN_GAUGES : WOUND_GAUGES;
                const isSingleton = singletonGauges?.has(`${sel.gauge}-${sel.type}`) ?? false;

                return (
                  <tr key={i} className={isSingleton ? 'singleton' : ''}>
                    <td className="string-num">{i + 1}</td>
                    <td>
                      <input
                        type="text"
                        value={note}
                        onChange={(e) => handleNoteChange(i, e.target.value)}
                        className="input input-sm note-input"
                      />
                    </td>
                    <td>
                      <select
                        value={sel.gauge}
                        onChange={(e) => handleGaugeChange(i, parseFloat(e.target.value))}
                        className="select gauge-select"
                      >
                        {gaugeOptions.map((g) => (
                          <option key={g} value={g}>
                            {formatGauge(g)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        value={sel.type}
                        onChange={(e) => handleTypeChange(i, e.target.value as 'p' | 'w')}
                        className="select type-select"
                      >
                        <option value="p">p</option>
                        <option value="w">w</option>
                      </select>
                    </td>
                    <td className={`tension-cell ${inRange ? 'in-range' : 'out-of-range'}`}>
                      {tension.toFixed(1)} lb
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
