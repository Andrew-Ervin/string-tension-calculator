// Global targets component
import { useApp } from '../context/AppContext';
import './GlobalTargets.css';

export function GlobalTargets() {
  const { state, dispatch } = useApp();
  const { globalTargetPlain, globalTargetWound } = state;

  const handlePlainChange = (idx: 0 | 1, value: number) => {
    const newPlain: [number, number] = [...globalTargetPlain];
    newPlain[idx] = value;
    dispatch({
      type: 'SET_GLOBAL_TARGETS',
      payload: { plain: newPlain, wound: globalTargetWound },
    });
  };

  const handleWoundChange = (idx: 0 | 1, value: number) => {
    const newWound: [number, number] = [...globalTargetWound];
    newWound[idx] = value;
    dispatch({
      type: 'SET_GLOBAL_TARGETS',
      payload: { plain: globalTargetPlain, wound: newWound },
    });
  };

  const applyToAll = () => {
    dispatch({ type: 'APPLY_GLOBAL_TARGETS' });
  };

  return (
    <div className="global-targets">
      <div className="target-group">
        <label>Plain target</label>
        <div className="target-inputs">
          <input
            type="number"
            value={globalTargetPlain[0]}
            onChange={(e) => handlePlainChange(0, parseFloat(e.target.value))}
            step={0.5}
            className="input input-xs"
          />
          <span>-</span>
          <input
            type="number"
            value={globalTargetPlain[1]}
            onChange={(e) => handlePlainChange(1, parseFloat(e.target.value))}
            step={0.5}
            className="input input-xs"
          />
          <span className="unit">lb</span>
        </div>
      </div>

      <div className="target-group">
        <label>Wound target</label>
        <div className="target-inputs">
          <input
            type="number"
            value={globalTargetWound[0]}
            onChange={(e) => handleWoundChange(0, parseFloat(e.target.value))}
            step={0.5}
            className="input input-xs"
          />
          <span>-</span>
          <input
            type="number"
            value={globalTargetWound[1]}
            onChange={(e) => handleWoundChange(1, parseFloat(e.target.value))}
            step={0.5}
            className="input input-xs"
          />
          <span className="unit">lb</span>
        </div>
      </div>

      <button className="btn btn-secondary btn-sm" onClick={applyToAll}>
        Apply to All
      </button>
    </div>
  );
}
