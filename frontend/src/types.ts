// Types for String Tension Calculator

export interface Guitar {
  name: string;
  n_strings: number;
  scale: number | [number, number]; // single or [treble, bass] for multiscale
  tuning: string[];
  string_types: string[] | null;
  target_plain: [number, number];
  target_wound: [number, number];
}

export interface StringSelection {
  gauge: number;
  type: 'p' | 'w';
}

export interface GuitarSelections {
  [guitarIndex: string]: StringSelection[];
}

export interface AppState {
  guitars: Guitar[];
  selections: GuitarSelections;
  globalTargetPlain: [number, number];
  globalTargetWound: [number, number];
}
