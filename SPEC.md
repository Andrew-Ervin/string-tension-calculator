# String Tension Calculator - Specification

## Overview

A guitar string tension calculator that helps guitarists find optimal string gauges for their instruments. The app calculates tension based on scale length, tuning, and string gauge, then optimizes gauge selection to minimize the number of unique gauges needed across multiple guitars while keeping tensions within target ranges.

## Core Concepts

### Tension Calculation

Tension is calculated using the formula:
```
tension = ((2 × scale × freq)² × μ) / 386.4
```
Where:
- `scale` = scale length in inches
- `freq` = frequency in Hz (derived from note)
- `μ` = unit weight (mass per unit length) - differs for plain vs wound strings
- `386.4` = gravitational constant conversion factor

### String Types

- **Plain (p)**: Unwound steel strings, typically used for higher strings
- **Wound (w)**: Wound strings with a core and wrap wire, typically used for lower strings

### Target Ranges

Users define acceptable tension ranges separately for plain and wound strings:
- **Plain target**: Default 13.0 - 15.5 lb
- **Wound target**: Default 16.0 - 20.0 lb

Strings within their target range are considered "good", strings outside are flagged.

## Data Inputs

### Guitar Specifications

Each guitar has:
- **Name**: Identifier for the guitar
- **Number of strings**: 4-12 strings supported
- **Scale length**: Single value (standard) or two values (multiscale: treble/bass)
- **Tuning**: Array of notes (e.g., ["E4", "B3", "G3", "D3", "A2", "E2"])
- **String types**: Optional override for which strings are plain vs wound (auto-detected if not specified)
- **Target plain**: [min, max] tension range for plain strings
- **Target wound**: [min, max] tension range for wound strings

### String Gauge Data

Two lookup tables of gauge → unit weight (μ):
- Plain gauges: .007 to .026
- Wound gauges: .024 to .080

## User Capabilities

### 1. View Summary

Display all guitars with their current gauge selections in a compact table:
- Rows = guitars
- Columns = string positions (1-N)
- Cells = gauge values, color-coded by string type (plain vs wound)
- Show tuning name for each guitar

### 2. View Gauge Inventory

Show all gauges currently in use across all guitars:
- Gauge value and type (plain/wound)
- Count of how many strings use this gauge
- For "singleton" gauges (count=1), show potential swap options that would:
  - Keep tension in range
  - Reduce unique gauge count by switching to an already-used gauge

### 3. Edit Guitar Properties

For each guitar, allow editing:
- Name
- Number of strings (adjusts tuning array)
- Scale length (single or multiscale)
- Individual string tunings (note input)
- Per-guitar target tension ranges
- Per-string gauge selection (dropdown of available gauges for that string type)
- Per-string type override (plain/wound)

### 4. Apply Global Targets

Set target ranges that apply to all guitars at once:
- Global plain target [min, max]
- Global wound target [min, max]
- "Apply to All" action updates all guitars

### 5. View Tension Feedback

For each string, show:
- Current tension value
- Visual indicator if in-range (green) or out-of-range (red)

### 6. Optimize Gauges

Run optimization algorithm that:
1. **Fixes out-of-range strings**: Replace gauges producing tension outside target with valid alternatives
2. **Consolidates singletons**: For gauges used only once, try to switch to a gauge already in use elsewhere (if it keeps tension in range)
3. **Minimizes unique gauges**: Prefer gauges that work for multiple strings

The optimizer should prefer making minimal changes from current selections while achieving better consolidation.

### 7. Add/Delete Guitars

- Add new guitar with default settings (inherits global targets)
- Delete existing guitar

### 8. Save Configuration

- Save current guitar specs to persistent storage
- Load guitar specs on app start

## Derived Calculations

### Note to Frequency

Convert note names to Hz:
- Format: `{Note}{Octave}` e.g., "E4", "Bb3", "F#2"
- Base: A4 = 440 Hz
- Formula: `freq = 440 × 2^((midi - 69) / 12)`

### Multiscale Interpolation

For multiscale guitars, interpolate scale length per string:
- String 1 (treble) = treble scale
- String N (bass) = bass scale
- Middle strings = linear interpolation

### Auto String Type Detection

Default assignment based on gauge recommendation:
- If recommended gauge for target tension is ≤ 0.022, string is plain
- Otherwise wound
- Typically strings 1-3 plain, 4+ wound for 6-string standard tuning

## UI Requirements

### Visual Design

- Dark theme (modern, easy on eyes)
- Clean typography
- Compact but readable tables
- Color coding:
  - Plain strings: muted/gray
  - Wound strings: accent color (green/teal)
  - In-range tension: green
  - Out-of-range tension: red/orange

### Responsiveness

- Desktop-first but usable on tablet
- Tables should be scrollable on smaller screens

### Interactions

- Dropdowns for gauge selection (filterable)
- Number inputs for targets and scale lengths
- Text inputs for notes
- Immediate tension recalculation on any change
- Button actions: Optimize, Save, Apply Global Targets, Add Guitar, Delete Guitar

## API Endpoints (Backend)

### GET /api/guitars
Returns list of all guitar specifications

### PUT /api/guitars
Save updated guitar specifications

### GET /api/gauges
Returns available plain and wound gauge options with unit weights

### POST /api/optimize
Input: Current guitar specs and selections
Output: Optimized gauge selections

### POST /api/tension
Input: gauge, type, scale, note
Output: calculated tension

## State Management

### Persistent State
- Guitar specifications (saved to file/database)

### Session State
- Current gauge selections per guitar
- Global target inputs

## File Structure (Reference)

Current data files:
- `guitar_specs.py` - Default guitar definitions
- `tension_data.py` - Gauge tables, calculation functions, optimization algorithm
