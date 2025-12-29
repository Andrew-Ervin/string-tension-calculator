// API service for communicating with the Flask backend
import type { Guitar, GuitarSelections } from '../types';

const API_BASE = '/api';

export async function fetchGuitars(): Promise<Guitar[]> {
  const response = await fetch(`${API_BASE}/guitars`);
  if (!response.ok) {
    throw new Error('Failed to fetch guitars');
  }
  return response.json();
}

export async function saveGuitars(guitars: Guitar[]): Promise<void> {
  const response = await fetch(`${API_BASE}/guitars`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(guitars),
  });
  if (!response.ok) {
    throw new Error('Failed to save guitars');
  }
}

export async function optimizeGauges(
  guitars: Guitar[],
  selections: GuitarSelections
): Promise<GuitarSelections> {
  const response = await fetch(`${API_BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ guitars, selections }),
  });
  if (!response.ok) {
    throw new Error('Failed to optimize gauges');
  }
  return response.json();
}
