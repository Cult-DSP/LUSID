## LUSID Agent Specification — Scene v0.5.1 → sonoPleth Renderer

**Updated:** 2026-02-09  
**Author:** LUSID / sonoPleth Integration Team  
**Purpose:** Agent-level instructions for implementing and maintaining the LUSID Scene pipeline. LUSID is now the **canonical scene format** — the C++ renderer reads LUSID directly. The old `renderInstructions.json` format is deprecated.

---

##  Architecture Summary

### New Pipeline (v0.5.1)

```
ADM WAV file
    │
    ├─► bwfmetaedit → currentMetaData.xml
    │
    ├─► checkAudioChannels.py → containsAudio.json
    │
    └─► sonoPleth parser.py → objectData.json, directSpeakerData.json, globalData.json
                                        │
                                        ▼
                              LUSID/src/xmlParser.py
                              (accepts parsed ADM dicts, outputs LUSID scene)
                                        │
                                        ▼
                          processedData/stageForRender/scene.lusid.json
                                        │
                                        ▼
                              C++ JSONLoader (reads LUSID directly)
                                        │
                                        ▼
                              SpatialRenderer → multichannel WAV
```

### What Changed from v0.5.0

1. **LUSID is the final output** — no more `renderInstructions.json` intermediate
2. **New node type: `direct_speaker`** — bed channels are now first-class LUSID nodes
3. **C++ renderer reads LUSID natively** — `JSONLoader` parses LUSID frame/node structure
4. **Node ID naming convention** — C++ uses `X.Y` node IDs, not `src_N` names
5. **`transcoder.py` is obsolete** — moved to `src/old_schema/`
6. **`createRenderInfo.py` is obsolete** — moved to `src/packageADM/old_schema/`

---

## 🏗️ LUSID Node Types

### `audio_object` (type: `"audio_object"`)
Spatial audio source with time-varying Cartesian position.
- **Fields:** `id`, `type`, `cart: [x, y, z]`, optional `gain`
- **ID convention:** `X.1` where X = group number
- **Renderer behavior:** Spatialized via VBAP/DBAP/LBAP

### `direct_speaker` (type: `"direct_speaker"`) — **NEW**
Fixed-position bed channel mapped to a speaker label.
- **Fields:** `id`, `type`, `cart: [x, y, z]`, `speakerLabel`, `channelID`
- **ID convention:** `X.1` where X = group number (groups 1–10 for standard Atmos bed)
- **Renderer behavior:** Treated as an `audio_object` with a single keyframe (static position). The `speakerLabel` field is informational metadata only — the renderer spatializes based on `cart`.

### `LFE` (type: `"LFE"`)
Low-frequency effects — routed directly to subwoofers, not spatialized.
- **Fields:** `id`, `type`
- **ID convention:** `X.1`
- **Renderer behavior:** Bypass spatialization, route to subwoofer channels
- **⚠️ DEV FLAG:** LFE is currently detected by hardcoded channel index (4th DirectSpeaker). Future update should detect by `speakerLabel` containing "LFE". See `_DEV_LFE_HARDCODED` flag in `xmlParser.py`.

### `spectral_features` (type: `"spectral_features"`)
Analysis metadata attached to parent audio_object group.
- **Fields:** `id`, `type`, plus arbitrary data keys (`centroid`, `flux`, `bandwidth`, etc.)
- **ID convention:** `X.2+` (child of group X)
- **Renderer behavior:** Ignored by renderer. Preserved in scene for analysis tools.

### `agent_state` (type: `"agent_state"`)
AI/agent metadata attached to parent audio_object group.
- **Fields:** `id`, `type`, plus arbitrary data keys (`mood`, `intensity`, etc.)
- **ID convention:** `X.2+` (child of group X)
- **Renderer behavior:** Ignored by renderer. Preserved in scene for analysis tools.

---

## 📄 LUSID Scene JSON Format (v0.5.1)

```json
{
  "version": "0.5",
  "sampleRate": 48000,
  "timeUnit": "seconds",
  "metadata": {
    "title": "Scene name",
    "sourceFormat": "ADM",
    "duration": "00:09:26.000"
  },
  "frames": [
    {
      "time": 0.0,
      "nodes": [
        {
          "id": "1.1",
          "type": "direct_speaker",
          "cart": [-1.0, 1.0, 0.0],
          "speakerLabel": "RC_L",
          "channelID": "AC_00011001"
        },
        {
          "id": "4.1",
          "type": "LFE"
        },
        {
          "id": "11.1",
          "type": "audio_object",
          "cart": [-0.975753, 1.0, 0.0]
        },
        {
          "id": "11.2",
          "type": "spectral_features",
          "centroid": 5000.0,
          "flux": 0.15
        }
      ]
    }
  ]
}
```

---

## 🔗 Source ↔ Audio File Mapping

### Node ID → WAV Filename
The stem splitter and renderer use node group IDs for file matching:

| Node ID | WAV File | Description |
|---------|----------|-------------|
| `1.1` | `1.1.wav` | DirectSpeaker Left |
| `4.1` | `LFE.wav` | LFE (special case) |
| `11.1` | `11.1.wav` | Audio object group 11 |

**Important:** The old `src_N` naming convention is deprecated. All source files are now named by their node ID (`X.Y.wav`) except LFE which remains `LFE.wav`.

---

## 🔧 C++ Renderer Integration

### JSONLoader reads LUSID directly
The new `JSONLoader::loadLusidScene()` method:
1. Parses LUSID JSON structure (version, sampleRate, timeUnit, frames, nodes)
2. Extracts `audio_object` and `direct_speaker` nodes → `SpatialData.sources`
3. Extracts `LFE` nodes → `SpatialData.sources["LFE"]`
4. Ignores `spectral_features` and `agent_state` nodes
5. Converts all timestamps to seconds using timeUnit + sampleRate
6. Source keys in `SpatialData.sources` use node group ID (e.g., `"1.1"`, `"11.1"`)

### Source WAV Loading
`WavUtils::loadSources()` matches source names from `SpatialData.sources` to WAV filenames:
- Source `"1.1"` → looks for `1.1.wav`
- Source `"LFE"` → looks for `LFE.wav`

---

## 📁 File Organization (After Migration)

### Files that moved to old_schema
```
LUSID/src/old_schema/
    transcoder.py              # Was: LUSID → renderInstructions.json
    test_transcoder.py         # Tests for the old transcoder

src/packageADM/old_schema/
    createRenderInfo.py        # Was: processedData → renderInstructions.json

spatial_engine/src/old_schema_loader/
    JSONLoader.cpp             # Was: renderInstructions.json parser
    JSONLoader.hpp
```

### New/Updated Files
```
LUSID/src/
    scene.py                   # Updated: + DirectSpeakerNode
    parser.py                  # Updated: + direct_speaker parsing
    xmlParser.py               # NEW: ADM data → LUSID scene
    __init__.py                # Updated: exports xmlParser + DirectSpeakerNode

spatial_engine/src/
    JSONLoader.cpp             # NEW: reads LUSID scene format
    JSONLoader.hpp             # NEW: updated SpatialData for LUSID
```

---

## ⚠️ Developer Notes & Flags

### `_DEV_LFE_HARDCODED` (in xmlParser.py)
LFE detection currently uses hardcoded index (4th DirectSpeaker channel). Set this flag to `False` when implementing speaker-label-based detection (`"LFE" in speakerLabel`).

### XML Parsing Dependency Decision (DEFERRED)
The LUSID `xmlParser.py` currently accepts **pre-parsed Python dicts** from sonoPleth's existing `parser.py` (which uses `lxml`). This avoids adding `lxml` as a LUSID dependency.

**Future evaluation needed:**
- Option A: Add `lxml` dependency to LUSID for direct XML parsing
- Option B: Use Python stdlib `xml.etree.ElementTree` (no dependency, slightly less robust namespaces)
- Option C: Keep current approach (sonoPleth parses, passes dicts to LUSID)

Decision deferred until real-world usage patterns are established. The current dict-based API keeps LUSID dependency-free.

### Intermediate Data Files
The pipeline still produces `objectData.json`, `directSpeakerData.json`, `globalData.json`, `containsAudio.json` as intermediate files. These are consumed by `xmlParser.py` to build the LUSID scene. Skipping these intermediate files is a future optimization.

---

##  Testing

```bash
# Run all LUSID tests
cd LUSID && python3 -m unittest discover -s tests -v

# Tests cover:
# - DirectSpeakerNode data model
# - Parser handling of direct_speaker type
# - xmlParser: ADM dicts → LUSID scene conversion
# - LFE detection (hardcoded + future label-based)
# - Node ID → source name mapping
# - All existing node types (audio_object, spectral_features, agent_state)
```

---

## ✅ v0.5.1 Implementation Status (2026-02-09)

### What Was Done This Session

**LUSID core (70 tests, all passing):**
- `DirectSpeakerNode` added to `scene.py` (type=`direct_speaker`, cart, speakerLabel, channelID)
- `parser.py` updated with `_parse_direct_speaker()` + validation (missing/NaN cart)
- `xmlParser.py` created — `adm_to_lusid_scene()` converts ADM dicts → LUSID scene
- `__init__.py` exports updated (transcoder → xmlParser)
- JSON schema updated with `direct_speaker` type
- `test_parser.py` — 42 tests (DirectSpeaker model, parsing, fixture)
- `test_xmlParser.py` — 28 tests (timecodes, LFE, mixed scenes, silent channels, round-trip, file I/O)
- Test fixture rewritten with direct_speaker (groups 1-3), LFE (group 4), audio_objects (groups 11-12)

**sonoPleth pipeline integration:**
- `packageForRender.py` — now calls `LUSID/src/xmlParser.load_processed_data_and_build_scene()` instead of `createRenderInfo`
- `splitStems.py` — WAV naming changed from `src_N.wav` to `X.1.wav` (LUSID node IDs), `_DEV_LFE_HARDCODED` flag added
- `createRender.py` — default path changed to `scene.lusid.json`
- `runPipeline.py` — uses `scene.lusid.json` path
- `runGUI.py` — uses `scene.lusid.json` path
- `createRenderInfo.py` — replaced with deprecation shim delegating to LUSID xmlParser

**C++ renderer:**
- `JSONLoader.cpp` rewritten with `loadLusidScene()` — parses LUSID frame/node structure
- `JSONLoader.hpp` updated with new method declaration
- `main.cpp` calls `loadLusidScene()` instead of `loadSpatialInstructions()`
- **Renderer rebuilt** (Feb 9) — confirmed working

**Old files archived to `old_schema/` subdirectories:**
- `LUSID/src/old_schema/transcoder.py`
- `LUSID/tests/old_schema/test_transcoder.py`
- `spatial_engine/src/old_schema_loader/JSONLoader.cpp/.hpp`
- `src/packageADM/old_schema/createRenderInfo.py`

**Documentation updated:**
- `LUSID/internalDocs/AGENTS.md` — this file
- `LUSID/internalDocs/DEVELOPMENT.md` — full rewrite
- `LUSID/README.md` — rewritten for v0.5.1
- `internalDocsMD/json_schema_info.md` — LUSID scene as primary, old format deprecated
- `internalDocsMD/RENDERING.md` — examples updated to `scene.lusid.json`
- `internalDocsMD/TODO.md` — stale references cleaned
- Top-level `README.md` — pipeline overview updated

### Pipeline Verified ✅

Tested with `SWALE-ATMOS-LFE.wav` → translab layout:
- **scene.lusid.json**: 2823 frames, 48kHz, 24 sources (1 LFE + 23 audio_objects)
- **Stem split**: 23 WAVs named `X.1.wav` + `LFE.wav` (correct)
- **C++ renderer**: Loaded 24 sources, rendered 193.2s to 18 channels (16 speakers + 2 subs)
- **Output**: 637 MB, no clipping, no silent channels, no NaN
- Bed channels (1-10) correctly empty — these ADM files have empty beds (expected)

### Stale file to clean up
- `processedData/stageForRender/renderInstructions.json` — leftover from old pipeline runs. Will be overwritten/ignored. Not harmful but can be deleted.

---

## 🎯 Next Steps

### Priority 1 — Immediate
- [ ] **Test with all ADM files** in `quickCommands.txt` (CANYON, SWALE, ASCENT, OFFERING) on both translab + allosphere layouts to confirm consistency
- [ ] **Delete stale `renderInstructions.json`** from `processedData/stageForRender/` and old `src_*.wav` files

### Priority 2 — Short-term
- [ ] **Label-based LFE detection** — set `_DEV_LFE_HARDCODED = False` and implement `speakerLabel` substring matching. Test with diverse ADM sources to confirm channel 4 assumption holds universally (or doesn't)
- [ ] **Clean up `splitStems.py` output path** — the hardcoded `outputPath = Path(os.path.abspath("processedData/stageForRender"))` should use the `output_dir` parameter instead (marked with `# SHOULD UPDATE THIS IN THE FUTURE` comment)
- [ ] **Spectral features pipeline** — wire up spectral analysis to populate `spectral_features` nodes in the LUSID scene (currently the schema + parser support it, but nothing generates them)

### Priority 3 — Medium-term
- [ ] **Eliminate intermediate JSON files** — have sonoPleth's `parser.py` pass dicts directly to `adm_to_lusid_scene()` instead of writing/reading `objectData.json`, `directSpeakerData.json`, `globalData.json` to disk
- [ ] **Evaluate XML parsing dependency** — decide whether LUSID should parse XML directly (lxml vs stdlib xml.etree vs keep current dict-based approach)
- [ ] **Agent state pipeline** — design how `agent_state` nodes get populated (AI/analysis hooks)
- [ ] **Gain per node** — the `gain` field on `audio_object` is defined but unused. Wire up ADM gain metadata if present.

### Priority 4 — Future
- [ ] **Additional node types** — `reverb_zone`, `interpolation_hint`, etc.
- [ ] **Performance** — optimize for large scenes (1000+ frames). Current: 2823 frames loads in <1ms
- [ ] **LUSID as standalone tool** — evaluate packaging LUSID as an independent Python package (pip installable)
