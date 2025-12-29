// Tension calculation utilities

import {
  A4,
  NOTE_INDEX,
  FLAT_TO_SHARP,
  PLAIN_UNIT_WEIGHTS,
  WOUND_UNIT_WEIGHTS,
  PLAIN_GAUGES,
  WOUND_GAUGES,
} from '../constants';

/**
 * Convert a note name to frequency in Hz
 * @param note - Note name like "E4", "Bb3", "F#2"
 * @returns Frequency in Hz
 */
export function noteToFreq(note: string): number {
  let name = note.slice(0, -1);
  const octave = parseInt(note.slice(-1), 10);
  
  if (name in FLAT_TO_SHARP) {
    name = FLAT_TO_SHARP[name];
  }
  
  const semitones = NOTE_INDEX[name] + (octave - 4) * 12;
  return A4 * Math.pow(2, semitones / 12);
}

/**
 * Calculate tension from unit weight
 * @param mu - Unit weight (mass per unit length)
 * @param scale - Scale length in inches
 * @param freq - Frequency in Hz
 * @returns Tension in pounds
 */
export function tensionFromMu(mu: number, scale: number, freq: number): number {
  return (Math.pow(2 * scale * freq, 2) * mu) / 386.4;
}

/**
 * Calculate tension for a given gauge, type, scale, and note
 */
export function calcTension(
  gauge: number,
  stype: 'p' | 'w',
  scale: number,
  freq: number
): number {
  const table = stype === 'p' ? PLAIN_UNIT_WEIGHTS : WOUND_UNIT_WEIGHTS;
  const mu = table[gauge] || 0;
  return tensionFromMu(mu, scale, freq);
}

/**
 * Resolve scale lengths for multiscale guitars
 * @param scale - Single scale or [treble, bass] tuple
 * @param nStrings - Number of strings
 * @returns Array of scale lengths per string
 */
export function resolveScales(
  scale: number | [number, number],
  nStrings: number
): number[] {
  if (typeof scale === 'number') {
    return Array(nStrings).fill(scale);
  }
  
  const [treble, bass] = scale;
  return Array.from({ length: nStrings }, (_, i) => 
    treble + (bass - treble) * i / (nStrings - 1)
  );
}

/**
 * Resolve string types (plain/wound)
 * @param stringTypes - Explicit types or null for auto
 * @param nStrings - Number of strings
 * @returns Array of 'p' or 'w' per string
 */
export function resolveStringTypes(
  stringTypes: string[] | null,
  nStrings: number
): ('p' | 'w')[] {
  if (stringTypes) {
    return stringTypes as ('p' | 'w')[];
  }
  // Default: first 3 strings plain, rest wound
  return Array.from({ length: nStrings }, (_, i) => 
    i < 3 ? 'p' : 'w'
  ) as ('p' | 'w')[];
}

/**
 * Get gauges that produce tension within the target range
 */
export function gaugesInRange(
  stype: 'p' | 'w',
  scale: number,
  freq: number,
  targetRange: [number, number]
): number[] {
  const table = stype === 'p' ? PLAIN_UNIT_WEIGHTS : WOUND_UNIT_WEIGHTS;
  const [minT, maxT] = targetRange;
  
  const valid: number[] = [];
  for (const [gaugeStr, mu] of Object.entries(table)) {
    const gauge = parseFloat(gaugeStr);
    const tension = tensionFromMu(mu, scale, freq);
    if (tension >= minT && tension <= maxT) {
      valid.push(gauge);
    }
  }
  
  return valid.sort((a, b) => a - b);
}

/**
 * Recommend the best gauge for a target tension
 */
export function recommendGauge(
  stype: 'p' | 'w',
  scale: number,
  freq: number,
  target: [number, number]
): number {
  const table = stype === 'p' ? PLAIN_UNIT_WEIGHTS : WOUND_UNIT_WEIGHTS;
  const gauges = stype === 'p' ? PLAIN_GAUGES : WOUND_GAUGES;
  const [minT, maxT] = target;
  const midpoint = (minT + maxT) / 2;
  
  // First, find gauges that are in range
  const inRange: [number, number][] = [];
  for (const gauge of gauges) {
    const mu = table[gauge];
    const actual = tensionFromMu(mu, scale, freq);
    if (actual >= minT && actual <= maxT) {
      inRange.push([gauge, actual]);
    }
  }
  
  // If we have in-range gauges, pick closest to midpoint
  if (inRange.length > 0) {
    let bestGauge = inRange[0][0];
    let bestError = Math.abs(inRange[0][1] - midpoint);
    for (const [gauge, actual] of inRange) {
      const error = Math.abs(actual - midpoint);
      if (error < bestError) {
        bestGauge = gauge;
        bestError = error;
      }
    }
    return bestGauge;
  }
  
  // Fallback: no gauge in range, pick closest to midpoint anyway
  let bestGauge = gauges[0];
  let bestError = Infinity;
  for (const gauge of gauges) {
    const mu = table[gauge];
    const actual = tensionFromMu(mu, scale, freq);
    const error = Math.abs(actual - midpoint);
    if (error < bestError) {
      bestGauge = gauge;
      bestError = error;
    }
  }
  
  return bestGauge;
}

/**
 * Format gauge as string (e.g., ".010")
 */
export function formatGauge(gauge: number): string {
  const str = gauge.toString();
  const digits = str.split('.')[1] || '';
  return '.' + digits.padEnd(3, '0');
}

/**
 * Get tuning name from array of notes
 */
export function tuningName(tuning: string[]): string {
  if (tuning.length === 0) return '';
  
  // Common tuning patterns
  const tuningStr = tuning.join('-');
  const patterns: Record<string, string> = {
    'E4-B3-G3-D3-A2-E2': 'Standard',
    'D4-A3-F3-C3-G2-D2': 'D Standard',
    'C4-G3-Eb3-Bb2-F2-C2': 'C Standard',
    'Eb4-Bb3-Gb3-Db3-Ab2-Eb2': 'Eb Standard',
    'C#4-G#3-E3-B2-F#2-C#2': 'C# Standard',
  };
  
  if (patterns[tuningStr]) {
    return patterns[tuningStr];
  }
  
  // Return first and last notes
  return `${tuning[0]}-${tuning[tuning.length - 1]}`;
}

/**
 * Check if tension is within target range
 */
export function isInRange(tension: number, target: [number, number]): boolean {
  return tension >= target[0] && tension <= target[1];
}
