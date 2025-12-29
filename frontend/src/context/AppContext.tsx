// Global state management using React Context
import { createContext, useContext, useReducer, useEffect, type ReactNode } from 'react';
import type { Guitar, GuitarSelections, StringSelection } from '../types';
import { DEFAULT_TARGET_PLAIN, DEFAULT_TARGET_WOUND } from '../constants';
import { 
  resolveScales, 
  resolveStringTypes, 
  noteToFreq, 
  recommendGauge 
} from '../utils/tension';
import { fetchGuitars, saveGuitars, optimizeGauges } from '../services/api';

interface AppState {
  guitars: Guitar[];
  selections: GuitarSelections;
  globalTargetPlain: [number, number];
  globalTargetWound: [number, number];
  loading: boolean;
  error: string | null;
}

type Action =
  | { type: 'SET_GUITARS'; payload: Guitar[] }
  | { type: 'SET_SELECTIONS'; payload: GuitarSelections }
  | { type: 'UPDATE_GUITAR'; payload: { index: number; guitar: Guitar } }
  | { type: 'UPDATE_STRING_SELECTION'; payload: { guitarIdx: number; stringIdx: number; selection: StringSelection } }
  | { type: 'ADD_GUITAR'; payload: Guitar }
  | { type: 'DELETE_GUITAR'; payload: number }
  | { type: 'SET_GLOBAL_TARGETS'; payload: { plain: [number, number]; wound: [number, number] } }
  | { type: 'APPLY_GLOBAL_TARGETS' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null };

const initialState: AppState = {
  guitars: [],
  selections: {},
  globalTargetPlain: DEFAULT_TARGET_PLAIN,
  globalTargetWound: DEFAULT_TARGET_WOUND,
  loading: true,
  error: null,
};

function generateDefaultSelections(guitars: Guitar[]): GuitarSelections {
  const selections: GuitarSelections = {};
  
  for (let idx = 0; idx < guitars.length; idx++) {
    const guitar = guitars[idx];
    const scales = resolveScales(guitar.scale, guitar.n_strings);
    const types = resolveStringTypes(guitar.string_types, guitar.n_strings);
    const guitarSelections: StringSelection[] = [];
    
    for (let i = 0; i < guitar.n_strings; i++) {
      const note = guitar.tuning[i] || 'E4';
      const scale = scales[i];
      const stype = types[i];
      const freq = noteToFreq(note);
      const target = stype === 'p' ? guitar.target_plain : guitar.target_wound;
      const gauge = recommendGauge(stype, scale, freq, target);
      guitarSelections.push({ gauge, type: stype });
    }
    
    selections[idx.toString()] = guitarSelections;
  }
  
  return selections;
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_GUITARS':
      return { ...state, guitars: action.payload, loading: false };
    
    case 'SET_SELECTIONS':
      return { ...state, selections: action.payload };
    
    case 'UPDATE_GUITAR': {
      const guitars = [...state.guitars];
      guitars[action.payload.index] = action.payload.guitar;
      return { ...state, guitars };
    }
    
    case 'UPDATE_STRING_SELECTION': {
      const { guitarIdx, stringIdx, selection } = action.payload;
      const newSelections = { ...state.selections };
      if (!newSelections[guitarIdx]) {
        newSelections[guitarIdx] = [];
      }
      newSelections[guitarIdx] = [...newSelections[guitarIdx]];
      newSelections[guitarIdx][stringIdx] = selection;
      return { ...state, selections: newSelections };
    }
    
    case 'ADD_GUITAR': {
      const guitars = [...state.guitars, action.payload];
      const selections = { ...state.selections };
      const idx = guitars.length - 1;
      const guitar = action.payload;
      const scales = resolveScales(guitar.scale, guitar.n_strings);
      const types = resolveStringTypes(guitar.string_types, guitar.n_strings);
      const guitarSelections: StringSelection[] = [];
      
      for (let i = 0; i < guitar.n_strings; i++) {
        const note = guitar.tuning[i] || 'E4';
        const scale = scales[i];
        const stype = types[i];
        const freq = noteToFreq(note);
        const target = stype === 'p' ? guitar.target_plain : guitar.target_wound;
        const gauge = recommendGauge(stype, scale, freq, target);
        guitarSelections.push({ gauge, type: stype });
      }
      
      selections[idx.toString()] = guitarSelections;
      return { ...state, guitars, selections };
    }
    
    case 'DELETE_GUITAR': {
      const guitars = state.guitars.filter((_, i) => i !== action.payload);
      const newSelections: GuitarSelections = {};
      // Re-index selections
      let newIdx = 0;
      for (let i = 0; i < state.guitars.length; i++) {
        if (i !== action.payload) {
          newSelections[newIdx.toString()] = state.selections[i.toString()];
          newIdx++;
        }
      }
      return { ...state, guitars, selections: newSelections };
    }
    
    case 'SET_GLOBAL_TARGETS':
      return {
        ...state,
        globalTargetPlain: action.payload.plain,
        globalTargetWound: action.payload.wound,
      };
    
    case 'APPLY_GLOBAL_TARGETS': {
      const guitars = state.guitars.map(g => ({
        ...g,
        target_plain: state.globalTargetPlain,
        target_wound: state.globalTargetWound,
      }));
      return { ...state, guitars };
    }
    
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  loadGuitars: () => Promise<void>;
  saveAllGuitars: () => Promise<void>;
  runOptimize: (guitarsOverride?: Guitar[]) => Promise<void>;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const loadGuitars = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const guitars = await fetchGuitars();
      dispatch({ type: 'SET_GUITARS', payload: guitars });
      const selections = generateDefaultSelections(guitars);
      // Run optimization on initial load
      const optimized = await optimizeGauges(guitars, selections);
      dispatch({ type: 'SET_SELECTIONS', payload: optimized });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err instanceof Error ? err.message : 'Failed to load guitars' });
    }
  };

  const saveAllGuitars = async () => {
    try {
      await saveGuitars(state.guitars);
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err instanceof Error ? err.message : 'Failed to save guitars' });
    }
  };

  const runOptimize = async (guitarsOverride?: Guitar[]) => {
    try {
      const guitarsToUse = guitarsOverride || state.guitars;
      const optimized = await optimizeGauges(guitarsToUse, state.selections);
      dispatch({ type: 'SET_SELECTIONS', payload: optimized });
    } catch (err) {
      dispatch({ type: 'SET_ERROR', payload: err instanceof Error ? err.message : 'Failed to optimize' });
    }
  };

  useEffect(() => {
    loadGuitars();
  }, []);

  return (
    <AppContext.Provider value={{ state, dispatch, loadGuitars, saveAllGuitars, runOptimize }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}
