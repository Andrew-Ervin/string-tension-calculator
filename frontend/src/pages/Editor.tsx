// Editor page - edit guitar properties and gauge selections
import { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { GuitarCard } from '../components/GuitarCard';
import { GlobalTargets } from '../components/GlobalTargets';
import type { Guitar } from '../types';
import './Editor.css';

export function Editor() {
  const { state, dispatch, saveAllGuitars, runOptimize } = useApp();
  const { guitars, selections } = state;
  const [expandedGuitar, setExpandedGuitar] = useState<number | null>(0);

  // Calculate singleton gauges (gauges used only once across all guitars)
  const singletonGauges = useMemo(() => {
    const gaugeCounts = new Map<string, number>();
    
    for (let gIdx = 0; gIdx < guitars.length; gIdx++) {
      const guitarSel = selections[gIdx.toString()] || [];
      for (const sel of guitarSel) {
        if (sel?.gauge) {
          const key = `${sel.gauge}-${sel.type}`;
          gaugeCounts.set(key, (gaugeCounts.get(key) || 0) + 1);
        }
      }
    }
    
    const singletons = new Set<string>();
    for (const [key, count] of gaugeCounts) {
      if (count === 1) {
        singletons.add(key);
      }
    }
    return singletons;
  }, [guitars, selections]);

  if (state.loading) {
    return <div className="loading">Loading...</div>;
  }

  if (state.error) {
    return <div className="error">{state.error}</div>;
  }

  const handleAddGuitar = () => {
    const newGuitar: Guitar = {
      name: `Guitar ${guitars.length + 1}`,
      n_strings: 6,
      scale: 25.5,
      tuning: ['E4', 'B3', 'G3', 'D3', 'A2', 'E2'],
      string_types: null,
      target_plain: state.globalTargetPlain,
      target_wound: state.globalTargetWound,
    };
    dispatch({ type: 'ADD_GUITAR', payload: newGuitar });
    setExpandedGuitar(guitars.length);
  };

  const handleDeleteGuitar = (index: number) => {
    if (confirm(`Delete "${guitars[index].name}"?`)) {
      dispatch({ type: 'DELETE_GUITAR', payload: index });
      if (expandedGuitar === index) {
        setExpandedGuitar(null);
      } else if (expandedGuitar !== null && expandedGuitar > index) {
        setExpandedGuitar(expandedGuitar - 1);
      }
    }
  };

  const handleSave = async () => {
    await saveAllGuitars();
    alert('Guitars saved!');
  };

  const handleOptimize = async () => {
    await runOptimize();
  };

  return (
    <div className="editor-page">
      <div className="editor-header">
        <GlobalTargets />
        <div className="editor-actions">
          <button className="btn btn-primary" onClick={handleOptimize}>
            Optimize
          </button>
          <button className="btn btn-secondary" onClick={handleSave}>
            Save
          </button>
          <button className="btn btn-ghost" onClick={handleAddGuitar}>
            Add Guitar
          </button>
        </div>
      </div>

      <div className="guitar-list">
        {guitars.length === 0 ? (
          <p className="text-muted">No guitars. Click "Add Guitar" to create one.</p>
        ) : (
          guitars.map((guitar, idx) => (
            <GuitarCard
              key={idx}
              guitar={guitar}
              index={idx}
              selections={selections[idx.toString()] || []}
              expanded={expandedGuitar === idx}
              onToggle={() => setExpandedGuitar(expandedGuitar === idx ? null : idx)}
              onDelete={() => handleDeleteGuitar(idx)}
              singletonGauges={singletonGauges}
            />
          ))
        )}
      </div>
    </div>
  );
}
