// Summary page - displays guitar overview and gauge inventory
import { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  resolveScales, 
  noteToFreq, 
  calcTension,
  formatGauge, 
  tuningName,
  isInRange,
} from '../utils/tension';
import { PLAIN_UNIT_WEIGHTS, WOUND_UNIT_WEIGHTS } from '../constants';
import './Summary.css';

interface UsageInfo {
  guitarIdx: number;
  guitarName: string;
  stringIdx: number;
  scale: number;
  freq: number;
  target: [number, number];
}

interface SwapOption {
  gauge: number;
  newTension: number;
  currentTension: number;
  tensionShift: number;
  direction: 'up' | 'down';
  targetMin: number;
  targetMax: number;
  inRange: boolean;
  requiredBound?: { type: 'min' | 'max'; value: number };
}

interface GaugeUsageWithSwap {
  gauge: number;
  type: 'p' | 'w';
  count: number;
  usages: UsageInfo[];
  swapOption?: SwapOption;
}

export function Summary() {
  const { state, dispatch, runOptimize } = useApp();
  const { guitars, selections, globalTargetPlain, globalTargetWound } = state;
  
  const [plainMin, setPlainMin] = useState(globalTargetPlain[0]);
  const [plainMax, setPlainMax] = useState(globalTargetPlain[1]);
  const [woundMin, setWoundMin] = useState(globalTargetWound[0]);
  const [woundMax, setWoundMax] = useState(globalTargetWound[1]);
  const [optimizing, setOptimizing] = useState(false);

  const handleOptimize = async () => {
    setOptimizing(true);
    
    // Build updated guitars with new bounds
    const updatedGuitars = guitars.map(g => ({
      ...g,
      target_plain: [plainMin, plainMax] as [number, number],
      target_wound: [woundMin, woundMax] as [number, number],
    }));
    
    // Update global state
    dispatch({
      type: 'SET_GLOBAL_TARGETS',
      payload: { plain: [plainMin, plainMax], wound: [woundMin, woundMax] },
    });
    dispatch({ type: 'SET_GUITARS', payload: updatedGuitars });
    
    // Run optimization with the updated guitars
    await runOptimize(updatedGuitars);
    setOptimizing(false);
  };

  if (state.loading) {
    return <div className="loading">Loading...</div>;
  }

  if (state.error) {
    return <div className="error">{state.error}</div>;
  }

  // Build gauge usage data with swap analysis
  const gaugeUsages = buildGaugeUsages();

  function buildGaugeUsages(): GaugeUsageWithSwap[] {
    const usageMap = new Map<string, GaugeUsageWithSwap>();

    // First pass: collect all gauge usages with string info
    for (let gIdx = 0; gIdx < guitars.length; gIdx++) {
      const guitar = guitars[gIdx];
      const guitarSel = selections[gIdx.toString()] || [];
      const scales = resolveScales(guitar.scale, guitar.n_strings);

      for (let sIdx = 0; sIdx < guitarSel.length; sIdx++) {
        const sel = guitarSel[sIdx];
        if (!sel?.gauge) continue;

        const note = guitar.tuning[sIdx] || 'E4';
        const scale = scales[sIdx];
        const freq = noteToFreq(note);
        const target = sel.type === 'p' ? guitar.target_plain : guitar.target_wound;

        const key = `${sel.gauge}-${sel.type}`;
        if (!usageMap.has(key)) {
          usageMap.set(key, {
            gauge: sel.gauge,
            type: sel.type,
            count: 0,
            usages: [],
          });
        }

        const usage = usageMap.get(key)!;
        usage.count++;
        usage.usages.push({
          guitarIdx: gIdx,
          guitarName: guitar.name,
          stringIdx: sIdx,
          scale,
          freq,
          target,
        });
      }
    }

    const usages = Array.from(usageMap.values());
    
    // Get set of common gauges (count > 1) for swap analysis
    const commonGauges = new Set<string>();
    for (const usage of usages) {
      if (usage.count > 1) {
        commonGauges.add(`${usage.gauge}-${usage.type}`);
      }
    }

    // Second pass: find swap options for singletons
    for (const usage of usages) {
      if (usage.count !== 1) continue;
      
      const { type, usages: stringUsages } = usage;
      const stringInfo = stringUsages[0];
      const { scale, freq, target } = stringInfo;
      const table = type === 'p' ? PLAIN_UNIT_WEIGHTS : WOUND_UNIT_WEIGHTS;
      
      // Current tension
      const currentTension = calcTension(usage.gauge, type, scale, freq);
      
      // Find best swap among common gauges of the same type
      // Choose the one with minimum tension deviation from current
      let bestSwap: SwapOption | null = null;
      let minDeviation = Infinity;
      
      // Check all common gauges of the same type
      for (const otherUsage of usages) {
        if (otherUsage.count <= 1) continue; // Only consider common gauges
        if (otherUsage.type !== type) continue; // Same type only
        if (otherUsage.gauge === usage.gauge) continue;
        
        const swapGauge = otherUsage.gauge;
        const mu = table[swapGauge];
        if (!mu) continue;
        
        const newTension = calcTension(swapGauge, type, scale, freq);
        const tensionShift = newTension - currentTension;
        const deviation = Math.abs(tensionShift);
        
        if (deviation < minDeviation) {
          minDeviation = deviation;
          const inRange = newTension >= target[0] && newTension <= target[1];
          let requiredBound: { type: 'min' | 'max'; value: number } | undefined;
          
          if (!inRange) {
            if (newTension < target[0]) {
              // Tension too low, need to lower the min
              requiredBound = { type: 'min', value: Math.floor(newTension * 2) / 2 };
            } else {
              // Tension too high, need to raise the max
              requiredBound = { type: 'max', value: Math.ceil(newTension * 2) / 2 };
            }
          }
          
          bestSwap = {
            gauge: swapGauge,
            newTension,
            currentTension,
            tensionShift,
            direction: tensionShift > 0 ? 'up' : 'down',
            targetMin: target[0],
            targetMax: target[1],
            inRange,
            requiredBound,
          };
        }
      }
      
      if (bestSwap) {
        usage.swapOption = bestSwap;
      }
    }

    return usages.sort((a, b) => a.gauge - b.gauge);
  }

  const maxStrings = guitars.length > 0 
    ? Math.max(...guitars.map(g => g.n_strings))
    : 0;

  return (
    <div className="summary-page">
      <section className="section">
        <h2>Guitar Overview</h2>
        {guitars.length === 0 ? (
          <p className="text-muted">No guitars defined. Go to Editor to add guitars.</p>
        ) : (
          <div className="table-container">
            <table className="guitar-table">
              <thead>
                <tr>
                  <th className="text-left">Guitar</th>
                  <th className="text-center">Tuning</th>
                  {Array.from({ length: maxStrings }, (_, i) => (
                    <th key={i} className="text-center string-col">{i + 1}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {guitars.map((guitar, gIdx) => {
                  const guitarSel = selections[gIdx.toString()] || [];
                  const scales = resolveScales(guitar.scale, guitar.n_strings);
                  
                  return (
                    <tr key={gIdx}>
                      <td className="text-left guitar-name">{guitar.name}</td>
                      <td className="text-center tuning">{tuningName(guitar.tuning)}</td>
                      {Array.from({ length: maxStrings }, (_, sIdx) => {
                        if (sIdx >= guitar.n_strings) {
                          return <td key={sIdx} className="text-center"></td>;
                        }
                        
                        const sel = guitarSel[sIdx];
                        if (!sel?.gauge) {
                          return <td key={sIdx} className="text-center">-</td>;
                        }

                        const note = guitar.tuning[sIdx] || 'E4';
                        const scale = scales[sIdx];
                        const freq = noteToFreq(note);
                        const tension = calcTension(sel.gauge, sel.type, scale, freq);
                        const target = sel.type === 'p' ? guitar.target_plain : guitar.target_wound;
                        const inRange = isInRange(tension, target);

                        return (
                          <td
                            key={sIdx}
                            className={`text-center gauge-cell ${sel.type === 'p' ? 'plain' : 'wound'} ${!inRange ? 'out-of-range' : ''}`}
                            title={`${tension.toFixed(1)} lb`}
                          >
                            {formatGauge(sel.gauge)}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="section">
        <h2>Gauge Inventory</h2>
        {gaugeUsages.length === 0 ? (
          <p className="text-muted">No gauge data.</p>
        ) : (
          <div className="table-container">
            <table className="inventory-table">
              <thead>
                <tr>
                  <th className="text-center">Gauge</th>
                  <th className="text-center">Type</th>
                  <th className="text-center">Count</th>
                  <th className="text-left">Used By</th>
                  <th className="text-center">Swap Option</th>
                </tr>
              </thead>
              <tbody>
                {gaugeUsages.map((usage) => (
                  <tr key={`${usage.gauge}-${usage.type}`} className={usage.count === 1 ? 'singleton' : ''}>
                    <td className={`text-center gauge-cell ${usage.type === 'p' ? 'plain' : 'wound'}`}>
                      {formatGauge(usage.gauge)}
                    </td>
                    <td className="text-center type-cell">{usage.type}</td>
                    <td className="text-center count-cell">{usage.count}</td>
                    <td className="text-left usage-list">
                      {usage.usages.map((u, i) => (
                        <span key={i} className="usage-item">
                          {u.guitarName} #{u.stringIdx + 1}
                          {i < usage.usages.length - 1 && ', '}
                        </span>
                      ))}
                    </td>
                    <td className="text-left swap-cell">
                      {usage.swapOption ? (
                        <div className={`swap-option ${usage.swapOption.inRange ? 'in-range' : 'out-of-range'}`}>
                          <span className="swap-to">
                            Use <strong>{formatGauge(usage.swapOption.gauge)}</strong>
                          </span>
                          <span className={`swap-delta ${usage.swapOption.direction}`}>
                            {usage.swapOption.direction === 'up' ? '↑' : '↓'}
                            {Math.abs(usage.swapOption.tensionShift).toFixed(1)} lb
                          </span>
                          {usage.swapOption.requiredBound && (
                            <span className="swap-required">
                              {usage.swapOption.requiredBound.type === 'min' ? 'min' : 'max'} → {usage.swapOption.requiredBound.value.toFixed(1)}
                            </span>
                          )}
                        </div>
                      ) : usage.count === 1 ? (
                        <span className="no-swap">no common gauge</span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="inventory-footer">
          <div className="stats">
            <span className="stat">
              <strong>{gaugeUsages.length}</strong> unique gauges
            </span>
            <span className="stat">
              <strong>{gaugeUsages.filter(u => u.count === 1).length}</strong> singletons
            </span>
          </div>
          
          <div className="global-bounds">
            <div className="bounds-group">
              <label>Plain</label>
              <div className="bounds-inputs">
                <input
                  type="number"
                  value={plainMin}
                  onChange={(e) => setPlainMin(parseFloat(e.target.value))}
                  step={0.5}
                  className="input-bound"
                />
                <span>–</span>
                <input
                  type="number"
                  value={plainMax}
                  onChange={(e) => setPlainMax(parseFloat(e.target.value))}
                  step={0.5}
                  className="input-bound"
                />
              </div>
            </div>
            
            <div className="bounds-group">
              <label>Wound</label>
              <div className="bounds-inputs">
                <input
                  type="number"
                  value={woundMin}
                  onChange={(e) => setWoundMin(parseFloat(e.target.value))}
                  step={0.5}
                  className="input-bound"
                />
                <span>–</span>
                <input
                  type="number"
                  value={woundMax}
                  onChange={(e) => setWoundMax(parseFloat(e.target.value))}
                  step={0.5}
                  className="input-bound"
                />
              </div>
            </div>
            
            <button
              className="btn-optimize"
              onClick={handleOptimize}
              disabled={optimizing}
            >
              {optimizing ? 'Optimizing...' : 'Optimize'}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
