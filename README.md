# LUSID Scene v0.5 — sonoPleth Integration

Python implementation of the LUSID Scene v0.5 format: a time-sequenced node graph for spatial audio.

## Overview

LUSID Scene v0.5 represents spatial audio scenes as a timeline of **frames**, each containing **nodes** with hierarchical IDs (`X.Y`) and typed data. This package provides:

- **Data model** (`src/scene.py`) — dataclasses for `LusidScene`, `Frame`, and node types
- **Parser** (`src/parser.py`) — load and validate LUSID JSON files with graceful fallback
- **Transcoder** (`src/transcoder.py`) — convert LUSID scenes to sonoPleth `renderInstructions.json`
- **JSON Schema** (`schema/lusid_scene_v0.5.schema.json`) — formal schema definition

## Quick Start

```python
from src import parse_file, transcode_to_sonopleth, extract_metadata_sidecar
import json

# Parse a LUSID scene
scene = parse_file("tests/fixtures/sample_scene_v0.5.json")

print(f"Frames: {scene.frame_count}")
print(f"Audio groups: {scene.audio_object_groups()}")
print(f"Has LFE: {scene.has_lfe()}")

# Transcode to sonoPleth renderInstructions
render = transcode_to_sonopleth(scene)
with open("renderInstructions.json", "w") as f:
    json.dump(render, f, indent=2)

# Extract metadata sidecar (spectral_features, agent_state)
sidecar = extract_metadata_sidecar(scene)
with open("lusid_metadata.json", "w") as f:
    json.dump(sidecar, f, indent=2)
```

Or use the file-based convenience function:

```python
from src import transcode_file

transcode_file(
    input_path="my_scene.json",
    output_path="renderInstructions.json",
    sidecar_path="lusid_metadata.json",
)
```

## Node Types

| Type | ID Convention | Description |
|------|--------------|-------------|
| `audio_object` | `X.1` | Spatial audio source with `cart` [x,y,z] direction vector |
| `LFE` | `X.1` | Low-frequency effects — routed to subwoofers, not spatialized |
| `spectral_features` | `X.2+` | Spectral analysis data (centroid, flux, bandwidth, etc.) |
| `agent_state` | `X.2+` | AI/agent metadata (mood, intensity, etc.) |

### Node ID Convention (`X.Y`)

- **X** = group number (logical grouping of related nodes)
- **Y** = hierarchy level (1 = parent/primary, 2+ = child/metadata)

Example: Group 1 has `1.1` (audio_object) + `1.2` (spectral_features). Group 3 has `3.1` (LFE).

## Transcoder Output

The transcoder converts LUSID frames → sonoPleth per-source keyframes:

- `audio_object` nodes → `src_<group>` entries with `{time, cart}` keyframes
- `LFE` nodes → single `"LFE": [{"time": 0.0}]` entry (no cart)
- `spectral_features` / `agent_state` → stripped from render output, written to sidecar

### sonoPleth Coordinate System

- `cart: [x, y, z]` — Cartesian direction vector
  - **x**: Left (−) / Right (+)
  - **y**: Back (−) / Front (+)
  - **z**: Down (−) / Up (+)
- Vectors are normalized to unit length by the renderer

## Time Units

Specify via the top-level `timeUnit` field:

| Value | Aliases | Description |
|-------|---------|-------------|
| `"seconds"` | `"s"` | Default. Timestamps in seconds |
| `"samples"` | `"samp"` | Sample indices (requires `sampleRate`) |
| `"milliseconds"` | `"ms"` | Timestamps in milliseconds |

The transcoder always outputs seconds regardless of input timeUnit.

## Validation

The parser warns but continues on:

- Missing `version` (assumes `"0.5"`)
- Unknown `timeUnit` (falls back to `"seconds"`)
- Nodes with missing `id`, invalid `id` format, missing `type`, unknown `type`
- `audio_object` with missing/invalid `cart` or NaN/Inf values
- Duplicate node IDs within a frame (keeps last)
- Unsorted frames (auto-sorted by time)

## Testing

```bash
cd LUSID
pip install pytest
pytest tests/ -v
```

## File Structure

```
LUSID/
├── schema/
│   └── lusid_scene_v0.5.schema.json
├── src/
│   ├── __init__.py
│   ├── scene.py          # Data model
│   ├── parser.py         # JSON loader + validator
│   └── transcoder.py     # LUSID → sonoPleth conversion
├── tests/
│   ├── fixtures/
│   │   └── sample_scene_v0.5.json
│   ├── test_parser.py
│   └── test_transcoder.py
├── transcoders/           # Existing format transcoders (ADM, AMBI, MPEGH)
├── utils/                 # Utilities (OSC, parsing helpers)
└── README.md
```

## Spec Reference

See `2-9-agentInfo.md` for the full LUSID Scene v0.5 specification.
See `AGENTS.md` for agent-level integration instructions.
