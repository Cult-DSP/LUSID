# LUSID Scene v0.5 — Development Notes

**Internal documentation for LUSID implementation**  
**Date:** February 9, 2026

---

## Implementation Summary

Successfully prototyped the LUSID Scene v0.5 structure inside the LUSID submodule repository. **53 tests, all passing, 0.003 seconds, zero external dependencies.** Everything uses Python stdlib only (`json`, `dataclasses`, `warnings`, `pathlib`, `math`, `unittest`).

LUSID has no venv, no `requirements.txt`, no pip installs needed. It's embeddable anywhere with Python 3.10+ (for the `dataclasses` + type hints).

---

## Architecture Overview

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| **Data Model** | `src/scene.py` | `LusidScene`, `Frame`, 4 node types (AudioObjectNode, LFENode, SpectralFeaturesNode, AgentStateNode) |
| **Parser** | `src/parser.py` | Load + validate LUSID JSON (warns, never crashes, graceful fallback) |
| **Transcoder** | `src/transcoder.py` | LUSID → sonoPleth `renderInstructions.json` + metadata sidecar |
| **Schema** | `schema/lusid_scene_v0.5.schema.json` | Formal JSON Schema for validation |
| **Tests** | `tests/` | 53 tests using stdlib `unittest` |

### Design Principles

1. **Lightweight**: No external dependencies, embeddable in any Python project
2. **Graceful Degradation**: Parser warns on issues but always returns a usable scene
3. **sonoPleth Compatible**: Direct transcoding to `renderInstructions.json` format
4. **Extensible**: Easy to add new node types or metadata fields
5. **Time-Accurate**: Support for seconds, samples, milliseconds with sample-rate conversion

---

## Node Types & ID Convention

### Node ID Format: `X.Y`
- **X** = group number (logical grouping of related nodes)  
- **Y** = hierarchy level (1 = parent/primary, 2+ = child/metadata)

### Supported Node Types

| Type | ID Pattern | Description | Output |
|------|------------|-------------|--------|
| `audio_object` | `X.1` | Spatial audio source with `cart` [x,y,z] direction | → `src_X` in renderInstructions |
| `LFE` | `X.1` | Low-frequency effects, no position | → `"LFE": [{"time": 0.0}]` |
| `spectral_features` | `X.2+` | Spectral analysis (centroid, flux, bandwidth) | → metadata sidecar only |
| `agent_state` | `X.2+` | AI/agent metadata (mood, intensity, etc.) | → metadata sidecar only |

**Example grouping:**
- Group 1: `1.1` (audio_object) + `1.2` (spectral_features)
- Group 2: `2.1` (audio_object) + `2.2` (agent_state)  
- Group 3: `3.1` (LFE)

---

## Transcoder Behavior

### LUSID → sonoPleth Conversion

1. **Audio Sources**: `audio_object` nodes → `src_<group>` entries with `{time, cart}` keyframes
2. **LFE Handling**: Any `LFE` node → single `"LFE": [{"time": 0.0}]` entry (no cart)
3. **Time Conversion**: All input timeUnits → seconds in output
4. **Metadata Stripping**: `spectral_features`/`agent_state` → removed from render output, written to optional sidecar

### Output Structure

**renderInstructions.json:**
```json
{
  "sampleRate": 48000,
  "timeUnit": "seconds", 
  "sources": {
    "src_1": [{"time": 0.0, "cart": [0, 1, 0]}, ...],
    "src_2": [{"time": 0.0, "cart": [1, 0, 0]}, ...],
    "LFE": [{"time": 0.0}]
  }
}
```

**Metadata sidecar (optional):**
```json
{
  "version": "0.5",
  "timeUnit": "seconds",
  "groups": {
    "1": {
      "spectral_features": [{"time": 0.0, "centroid": 5000, "flux": 0.15}],
      "agent_state": [{"time": 0.0, "mood": "calm"}]
    }
  }
}
```

---

## Validation & Error Handling

### Parser Warnings (Non-Fatal)

The parser issues warnings but continues processing:

- Missing `version` → assumes `"0.5"`
- Unknown `timeUnit` → falls back to `"seconds"`  
- Missing/invalid node `id` → skip node
- Invalid `cart` (NaN/Inf) → skip audio_object
- Duplicate node IDs within frame → keep last
- Unsorted frames → auto-sort by time

### Time Unit Support

| Input | Aliases | Conversion to Seconds |
|-------|---------|----------------------|
| `"seconds"` | `"s"` | Direct (1:1) |
| `"milliseconds"` | `"ms"` | × 0.001 |
| `"samples"` | `"samp"` | ÷ sampleRate (requires valid sampleRate) |

---

## Testing Coverage

### Test Structure
- **test_parser.py**: 35 tests (data model, parser validation, fixture loading)
- **test_transcoder.py**: 18 tests (output format, LFE handling, time conversion, metadata sidecar)

### Key Test Scenarios
- Node ID validation (`X.Y` pattern enforcement)
- Time unit conversion accuracy  
- LFE source handling (no `cart` in output)
- Metadata stripping from render output
- Frame sorting by timestamp
- Warning generation for malformed data
- Graceful handling of missing/invalid fields

### Running Tests
```bash
cd LUSID && python3 -m unittest discover -s tests -v
# 53 tests, ~0.003s runtime
```

---

## File Structure

```
LUSID/
├── schema/
│   └── lusid_scene_v0.5.schema.json     # JSON Schema definition
├── src/
│   ├── __init__.py                       # Public API exports
│   ├── scene.py                          # Data model classes
│   ├── parser.py                         # JSON loader + validator  
│   └── transcoder.py                     # LUSID → sonoPleth conversion
├── tests/
│   ├── fixtures/
│   │   └── sample_scene_v0.5.json        # 5-frame test scene
│   ├── test_parser.py                    # Parser + data model tests
│   └── test_transcoder.py                # Transcoder tests
├── internalDocs/
│   ├── conceptNotes.md                   # Original scene structure notes
│   └── DEVELOPMENT.md                    # This file
├── transcoders/                          # Existing format transcoders
├── utils/                                # Utilities (OSC, parsing helpers)
├── README.md                             # User-facing documentation
├── 2-9-agentInfo.md                      # Full LUSID Scene v0.5 specification
└── AGENTS.md                             # Agent-level integration instructions
```

---

## Usage Examples

### Basic Transcoding
```python
from src import transcode_file

transcode_file(
    input_path="my_scene.json",
    output_path="renderInstructions.json", 
    sidecar_path="lusid_metadata.json",
)
```

### Programmatic API
```python
from src import parse_file, transcode_to_sonopleth, extract_metadata_sidecar

scene = parse_file("scene.json")
render = transcode_to_sonopleth(scene)
sidecar = extract_metadata_sidecar(scene)

print(f"Audio groups: {scene.audio_object_groups()}")
print(f"Has LFE: {scene.has_lfe()}")
```

---

## sonoPleth Integration Points

### Coordinate System Alignment
- LUSID `cart: [x, y, z]` maps directly to sonoPleth direction vectors
- **x**: Left (−) / Right (+)
- **y**: Back (−) / Front (+)  
- **z**: Down (−) / Up (+)
- Vectors normalized to unit length by sonoPleth renderer

### LFE Special Handling
- LUSID `LFE` nodes → sonoPleth `"LFE"` source name
- Bypasses spatialization, routes to subwoofers
- Single keyframe at t=0, no `cart` field (matches sonoPleth convention)

### Source Naming Convention
- LUSID group 1 → `src_1`
- LUSID group 2 → `src_2` 
- etc.
- Maintains audio file matching: `src_1.wav`, `src_2.wav`

---

## Future Development Notes

### Planned Extensions
1. **Additional Node Types**: Could add `reverb_zone`, `occlusion_data`, `binaural_filter`
2. **Interpolation Hints**: Add per-node interpolation mode (`linear`, `step`, `spline`)
3. **Buffer Optimization**: Implement glTF-style binary buffers for large time-series
4. **Schema Versioning**: Prepare for v0.6+ with backward compatibility

### Integration Opportunities
1. **Real-time Streaming**: JSON → WebSocket for live LUSID scene updates
2. **DAW Plugins**: Export from Reaper/ProTools → LUSID → sonoPleth
3. **Game Engines**: Unity/Unreal → LUSID for spatial audio previews
4. **Analysis Tools**: sonoPleth renders → LUSID for scene reconstruction

### Performance Considerations
- Current implementation optimized for correctness over speed
- Large scenes (1000+ frames) may benefit from streaming parser
- Memory usage scales with frame count × node count
- Consider lazy loading for massive time-series datasets

---

## Implementation Status

✅ **Completed**
- Core data model with all 4 node types
- Full parser with validation and graceful fallback
- Complete transcoder (LUSID → sonoPleth + metadata sidecar)
- Comprehensive test suite (53 tests, 100% pass)
- JSON Schema for validation
- Documentation (README + this dev doc)

🔄 **Ready for Integration**
- Zero external dependencies
- Compatible with existing sonoPleth pipeline
- Embeddable in other projects
- Extensible for future node types

🎯 **Next Steps**
- Test with real ADM → LUSID → sonoPleth workflow
- Validate LFE routing in actual renders
- Consider performance optimizations for large scenes
- Gather feedback from actual usage patterns