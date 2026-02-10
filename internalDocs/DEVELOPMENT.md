# LUSID Scene v0.5.1 — Development Notes

**Internal documentation for LUSID implementation**  
**Last Updated:** February 9, 2026

---

## Implementation Summary

LUSID Scene v0.5.1 is the **canonical scene format** for sonoPleth spatial audio rendering. The C++ renderer reads LUSID JSON directly — the old `renderInstructions.json` intermediate format is deprecated and moved to `old_schema/` directories.

**Status:** 70 tests, all passing, zero external dependencies. Python stdlib only (`json`, `dataclasses`, `warnings`, `pathlib`, `math`, `unittest`).

---

## Architecture Overview

### Pipeline Flow

```
ADM WAV ─► bwfmetaedit ─► XML ─► sonoPleth parser.py ─► intermediate JSONs
                                                              │
                ┌─────────────────────────────────────────────┘
                ▼
        LUSID/src/xmlParser.py  (accepts dicts from sonoPleth's parser)
                │
                ▼
        scene.lusid.json  (processedData/stageForRender/)
                │
                ├──► C++ JSONLoader::loadLusidScene()
                │         │
                │         ▼
                │    SpatialRenderer → multichannel WAV
                │
                └──► (optional) metadata sidecar for analysis
```

### Core Components

| Component      | File                                  | Purpose                                                                                                 |
| -------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Data Model** | `src/scene.py`                        | `LusidScene`, `Frame`, 5 node types (AudioObject, **DirectSpeaker**, LFE, SpectralFeatures, AgentState) |
| **Parser**     | `src/parser.py`                       | Load + validate LUSID JSON (warns, never crashes, graceful fallback)                                    |
| **XML Parser** | `src/xmlParser.py`                    | **NEW** — Converts pre-parsed ADM data dicts → LUSID scene                                              |
| **Schema**     | `schema/lusid_scene_v0.5.schema.json` | Formal JSON Schema for validation                                                                       |
| **Tests**      | `tests/`                              | unittest tests using stdlib only                                                                        |

### Obsolete Components (moved to old_schema/)

| Component             | Old Location               | New Location                            | Reason                                              |
| --------------------- | -------------------------- | --------------------------------------- | --------------------------------------------------- |
| `transcoder.py`       | `src/transcoder.py`        | `src/old_schema/transcoder.py`          | LUSID → renderInstructions no longer needed         |
| `test_transcoder.py`  | `tests/test_transcoder.py` | `tests/old_schema/test_transcoder.py`   | Tests for obsolete transcoder                       |
| `createRenderInfo.py` | `src/packageADM/`          | `src/packageADM/old_schema/`            | processedData → renderInstructions no longer needed |
| `JSONLoader.cpp/.hpp` | `spatial_engine/src/`      | `spatial_engine/src/old_schema_loader/` | renderInstructions.json C++ parser                  |

### Components to Archive (XML Migration)

| Component             | Current Location           | Archive Location                        | Reason                                              |
| --------------------- | -------------------------- | --------------------------------------- | --------------------------------------------------- |
| `xmlParser.py`        | `src/xmlParser.py`         | `src/old_XML_parse/xmlParser.py`        | Replaced by `xml_etree_parser.py` (single-step)     |
| `test_xmlParser.py`   | `tests/test_xmlParser.py`  | `tests/old_XML_parse/test_xmlParser.py` | Tests for obsolete dict-based parser                |
| Modified pipeline files | `src/analyzeADM/`, `src/packageADM/`, root | `old_XML_parse/` subdirs          | Dict intermediaries eliminated, JSON I/O removed    |

### Design Principles

1. **Lightweight**: No external dependencies, embeddable in any Python project
2. **Graceful Degradation**: Parser warns on issues but always returns a usable scene
3. **LUSID is the Source of Truth**: C++ renderer reads LUSID directly — no intermediate format
4. **Extensible**: Easy to add new node types or metadata fields
5. **Time-Accurate**: Support for seconds, samples, milliseconds with sample-rate conversion

---

## Node Types & ID Convention

### Node ID Format: `X.Y`

- **X** = group number (logical grouping of related nodes)
- **Y** = hierarchy level (1 = parent/primary, 2+ = child/metadata)

### Channel Assignment Convention

- **Groups 1–10**: DirectSpeaker bed channels (standard Atmos bed)
- **Group 4**: LFE (hardcoded — see DEV FLAG below)
- **Groups 11+**: Audio objects (spatial sources from ADM)

### Supported Node Types

| Type                | ID Pattern | Description                               | Renderer Behavior                             |
| ------------------- | ---------- | ----------------------------------------- | --------------------------------------------- |
| `audio_object`      | `X.1`      | Spatial source with `cart` [x,y,z]        | Spatialized (VBAP/DBAP/LBAP)                  |
| `direct_speaker`    | `X.1`      | **NEW** — Bed channel with fixed position | Treated as static audio_object (1 keyframe)   |
| `LFE`               | `X.1`      | Low-frequency effects, no position        | Routes to subwoofers, bypasses spatialization |
| `spectral_features` | `X.2+`     | Spectral analysis data                    | Ignored by renderer                           |
| `agent_state`       | `X.2+`     | AI/agent metadata                         | Ignored by renderer                           |

### Source ↔ WAV File Mapping

| Node ID | WAV Filename | Notes                      |
| ------- | ------------ | -------------------------- |
| `1.1`   | `1.1.wav`    | DirectSpeaker (e.g., Left) |
| `4.1`   | `LFE.wav`    | LFE (special naming)       |
| `11.1`  | `11.1.wav`   | Audio object               |

**Note:** Old `src_N` naming convention is deprecated. Files are named by node ID.

---

## xmlParser — ADM Data → LUSID Scene

### How It Works

`xmlParser.py` accepts **pre-parsed Python dicts** from sonoPleth's existing `parser.py` (which uses `lxml` to parse the ADM XML). This avoids adding `lxml` as a LUSID dependency.

**Input:** 4 dicts from sonoPleth's intermediate data

- `objectData` — spatial audio objects with time-varying positions
- `directSpeakerData` — fixed bed channel positions
- `globalData` — sample rate, duration, format info
- `containsAudio` — per-channel audio detection (skips silent channels)

**Output:** `LusidScene` object → serialized as `scene.lusid.json`

### Channel → Group Mapping

```
DirectSpeakers (1-indexed from XML order):
  Channel 1 → Group 1 → "1.1" (direct_speaker)
  Channel 2 → Group 2 → "2.1" (direct_speaker)
  Channel 3 → Group 3 → "3.1" (direct_speaker)
  Channel 4 → Group 4 → "4.1" (LFE)  ← hardcoded, see DEV FLAG
  ...
  Channel 10 → Group 10 → "10.1" (direct_speaker)

Audio Objects (continue numbering):
  Object 1 → Group 11 → "11.1" (audio_object)
  Object 2 → Group 12 → "12.1" (audio_object)
  ...
```

---

## C++ Integration

### JSONLoader (New — reads LUSID)

The new `JSONLoader::loadLusidScene()` method replaces the old `loadSpatialInstructions()`:

1. Opens LUSID JSON, parses `version`, `sampleRate`, `timeUnit`
2. Iterates `frames[]` → for each frame, iterates `nodes[]`
3. `audio_object` and `direct_speaker` nodes → accumulated into `SpatialData.sources[nodeId]`
4. `LFE` nodes → `SpatialData.sources["LFE"]`
5. `spectral_features` / `agent_state` → ignored
6. Timestamps converted to seconds using timeUnit + sampleRate
7. Source keys use node ID format (`"1.1"`, `"11.1"`) not `src_N`

### SpatialData struct unchanged

The `SpatialData` struct (sampleRate, timeUnit, sources map) stays the same. Only the source key naming changes.

---

## Validation & Error Handling

### Parser Warnings (Non-Fatal)

- Missing `version` → assumes `"0.5"`
- Unknown `timeUnit` → falls back to `"seconds"`
- Missing/invalid node `id` → skip node
- Invalid `cart` (NaN/Inf) → skip audio_object / direct_speaker
- Duplicate node IDs within frame → keep last
- Unsorted frames → auto-sort by time
- Unknown node type → skip with warning

### xmlParser Warnings (Non-Fatal)

- Silent channel detected → skip (with message)
- Missing directSpeakerData → no direct_speaker nodes emitted
- Missing objectData → no audio_object nodes emitted
- Missing globalData → default sampleRate=48000

---

## ⚠️ Developer Flags

### `_DEV_LFE_HARDCODED = True` (xmlParser.py)

**Current behavior:** LFE is detected as the 4th DirectSpeaker (index 4).
**Future behavior:** When set to `False`, detect LFE by checking `speakerLabel` for "LFE" substring.
**Why deferred:** All current ADM files have LFE at channel 4. Label-based detection needs testing with diverse ADM sources.

### XML Parsing Dependency Decision (RESOLVED)

**Decision: Adopt `xml.etree.ElementTree` (stdlib)**

- ✅ **Benchmark Results**: 2.3x faster than lxml pipeline, 5.5x more memory usage
- ✅ **Memory Trade-off**: Acceptable for ADM XML sizes (10-30MB typical, 100MB max)
- ✅ **Zero Dependencies**: Keeps LUSID embeddable with stdlib only
- ✅ **Output Parity**: Confirmed identical LUSID scenes from both parsers

**Implementation**: New `xml_etree_parser.py` provides single-step XML → LUSID conversion, eliminating intermediate JSON I/O.

---

## Testing

### Running Tests

```bash
cd LUSID && python3 -m unittest discover -s tests -v
```

### Test Coverage

- **test_parser.py**: Data model, LUSID JSON parsing, direct_speaker support, validation
- **test_xmlParser.py**: ADM dicts → LUSID scene conversion, channel mapping, LFE handling, silent channel skipping

### Old Schema Tests

Tests for the obsolete transcoder are preserved in `tests/old_schema/test_transcoder.py` for reference.

---

## File Structure

```
LUSID/
├── schema/
│   └── lusid_scene_v0.5.schema.json     # JSON Schema (updated for direct_speaker)
├── src/
│   ├── __init__.py                       # Public API exports
│   ├── scene.py                          # Data model (5 node types)
│   ├── parser.py                         # LUSID JSON loader + validator
│   ├── xmlParser.py                      # LEGACY: ADM dicts → LUSID scene (to be archived)
│   ├── xml_etree_parser.py               # NEW: Single-step XML → LUSID (stdlib only)
│   └── old_XML_parse/                    # ARCHIVED: Obsolete lxml/dict-based parsers
│       └── xmlParser.py                  # Archived dict-based parser
├── tests/
│   ├── fixtures/
│   │   └── sample_scene_v0.5.json        # Test scene (updated w/ direct_speaker)
│   ├── test_parser.py                    # Parser + data model tests
│   ├── test_xmlParser.py                 # LEGACY: xmlParser tests (to be archived)
│   ├── test_xml_etree_parser.py          # NEW: xml_etree_parser tests
│   ├── benchmark_xml_parsers.py          # Performance comparison script
│   └── old_XML_parse/                    # ARCHIVED: Tests for obsolete parsers
│       └── test_xmlParser.py             # Archived xmlParser tests
├── internalDocs/
│   ├── conceptNotes.md                   # Original scene structure notes
│   ├── AGENTS.md                         # Agent-level specification + archival plan
│   └── DEVELOPMENT.md                    # This file
└── README.md                             # User-facing documentation
```

---

## Implementation Status

✅ **Completed (v0.5.0)**

- Core data model with 4 node types
- Full parser with validation and graceful fallback
- Comprehensive test suite
- JSON Schema for validation

✅ **Completed (v0.5.1)**

- `DirectSpeakerNode` type added to data model
- `xmlParser.py` — ADM data → LUSID scene conversion
- Old schema files archived to `old_schema/` directories
- New C++ `JSONLoader` reads LUSID format directly
- Node ID naming convention (`X.Y`) replaces `src_N`
- Updated stem splitter for new naming
- Documentation updated (AGENTS.md, DEVELOPMENT.md)

✅ **Completed (XML Migration v0.5.2)**

- `xml_etree_parser.py` — Single-step XML → LUSID using stdlib only
- Eliminated intermediate JSON files (dicts flow in memory)
- Benchmark vs lxml: 2.3x faster, output parity confirmed
- Added 36 tests (106 total passing)
- Updated pipeline to pass dicts directly (no JSON I/O)
- Resolved XML dependency decision: stdlib `xml.etree.ElementTree`

🎯 **Future Work**

- Archive obsolete lxml/dict-based files to `old_XML_parse/` directories
- Integrate `xml_etree_parser` into main pipeline (replace dict intermediaries)
- Create `LusidScene.summary()` debug method
- Implement label-based LFE detection (disable `_DEV_LFE_HARDCODED`)
- Evaluate full `lxml` removal from sonoPleth venv
- Performance optimizations for large scenes
- Additional node types (reverb_zone, interpolation hints, etc.)
