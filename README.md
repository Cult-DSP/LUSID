# LUSID Scene v0.5.2 — sonoPleth Integration

Python implementation of the LUSID Scene v0.5 format: a time-sequenced node graph for spatial audio.

## Overview

LUSID Scene v0.5 represents spatial audio scenes as a timeline of **frames**, each containing **nodes** with hierarchical IDs (`X.Y`) and typed data. The LUSID scene (`scene.lusid.json`) is the **canonical spatial data format** — the C++ renderer reads it directly.

This package provides:

- **Data model** (`src/scene.py`) — dataclasses for `LusidScene`, `Frame`, and 5 node types
- **Parser** (`src/parser.py`) — load and validate LUSID JSON files with graceful fallback
- **XML Parser** (`src/xml_etree_parser.py`) — parse ADM XML directly into LUSID scenes (stdlib only)
- **JSON Schema** (`schema/lusid_scene_v0.5.schema.json`) — formal schema definition

**Zero external dependencies** — stdlib only (`json`, `dataclasses`, `warnings`, `pathlib`, `math`).
\*\* Currently reliant on xml dependency used in sonoPleth.

## Quick Start

```python
from src import parse_file, adm_to_lusid_scene, write_lusid_scene

# Parse an existing LUSID scene
scene = parse_file("tests/fixtures/sample_scene_v0.5.json")

print(f"Frames: {scene.frame_count}")
print(f"Audio object groups: {scene.audio_object_groups()}")
print(f"Direct speaker groups: {scene.direct_speaker_groups()}")
print(f"Has LFE: {scene.has_lfe()}")
```

### Build a LUSID scene from ADM data

```python
from src import adm_to_lusid_scene, write_lusid_scene

# Pre-parsed ADM dicts (from sonoPleth's parser.py)
scene = adm_to_lusid_scene(
    object_data=objectData,
    direct_speaker_data=directSpeakerData,
    global_data=globalData,
    contains_audio=containsAudio,
)
write_lusid_scene(scene, "processedData/stageForRender/scene.lusid.json")
```

Or use the convenience function that loads intermediate JSONs directly:

```python
from src.xmlParser import load_processed_data_and_build_scene

scene = load_processed_data_and_build_scene(
    processed_dir="processedData",
    output_path="processedData/stageForRender/scene.lusid.json",
)
```

## Node Types

| Type                | ID Convention | Description                                                   |
| ------------------- | ------------- | ------------------------------------------------------------- |
| `direct_speaker`    | `X.1`         | Fixed bed channel with `cart`, `speakerLabel`, `channelID`    |
| `audio_object`      | `X.1`         | Spatial audio source with time-varying `cart` [x,y,z]         |
| `LFE`               | `X.1`         | Low-frequency effects — routed to subwoofers, not spatialized |
| `spectral_features` | `X.2+`        | Spectral analysis data (centroid, flux, bandwidth, etc.)      |
| `agent_state`       | `X.2+`        | AI/agent metadata (mood, intensity, etc.)                     |

### Node ID Convention (`X.Y`)

- **X** = group number (logical grouping of related nodes)
- **Y** = hierarchy level (1 = parent/primary, 2+ = child/metadata)

Groups 1–10: DirectSpeaker bed channels. Group 4: LFE (hardcoded). Groups 11+: Audio objects.

### Source ↔ WAV File Mapping

| Node ID | WAV File   | Description                |
| ------- | ---------- | -------------------------- |
| `1.1`   | `1.1.wav`  | DirectSpeaker (e.g., Left) |
| `4.1`   | `LFE.wav`  | LFE (special naming)       |
| `11.1`  | `11.1.wav` | Audio object               |

## Coordinate System

- `cart: [x, y, z]` — Cartesian direction vector
  - **x**: Left (−) / Right (+)
  - **y**: Back (−) / Front (+)
  - **z**: Down (−) / Up (+)
- Vectors are normalized to unit length by the renderer

## Time Units

Specify via the top-level `timeUnit` field:

| Value            | Aliases  | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `"seconds"`      | `"s"`    | Default. Timestamps in seconds         |
| `"samples"`      | `"samp"` | Sample indices (requires `sampleRate`) |
| `"milliseconds"` | `"ms"`   | Timestamps in milliseconds             |

## Validation

The parser warns but continues on:

- Missing `version` (assumes `"0.5"`)
- Unknown `timeUnit` (falls back to `"seconds"`)
- Nodes with missing `id`, invalid `id` format, missing `type`, unknown `type`
- `audio_object`/`direct_speaker` with missing/invalid `cart` or NaN/Inf values
- Duplicate node IDs within a frame (keeps last)
- Unsorted frames (auto-sorted by time)

## Testing

```bash
cd LUSID
python3 -m unittest discover -s tests -v
```

70 tests covering data model, parser, xmlParser, validation, round-trips.

## File Structure

```
LUSID/
├── schema/
│   └── lusid_scene_v0.5.schema.json     # JSON Schema
├── src/
│   ├── __init__.py                       # Public API exports
│   ├── scene.py                          # Data model (5 node types)
│   ├── parser.py                         # LUSID JSON loader + validator
│   ├── xml_etree_parser.py               # ADM XML → LUSID scene (stdlib)
│   └── old_schema/
│       └── transcoder.py                 # OBSOLETE: LUSID → renderInstructions
├── tests/
│   ├── fixtures/
│   │   └── sample_scene_v0.5.json
│   ├── test_parser.py                    # Parser + data model tests (42)
│   ├── test_xml_etree_parser.py           # XML parser tests (36)
│   └── old_schema/
│       └── test_transcoder.py            # OBSOLETE
└── internalDocs/
    ├── AGENTS.md                         # Agent-level specification
    ├── DEVELOPMENT.md                    # Development notes
    └── conceptNotes.md                   # Original design notes
```

## See Also

- `internalDocs/AGENTS.md` — Agent-level integration instructions
- `internalDocs/DEVELOPMENT.md` — Development notes and architecture
