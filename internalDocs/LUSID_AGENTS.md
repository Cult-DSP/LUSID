## LUSID Agent Specification — Scene v0.5.2 → sonoPleth Renderer

**Updated:** 2026-02-13  
**Author:** LUSID / sonoPleth Integration Team  
**Purpose:** Agent-level instructions for implementing and maintaining the LUSID Scene pipeline. LUSID is now the **canonical scene format** — the C++ renderer reads LUSID directly. The old `renderInstructions.json` format is deprecated.

---

## Architecture Summary

### New Pipeline (v0.5.2)

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
                              LUSID/src/xml_etree_parser.py
                              (parses ADM XML directly, outputs LUSID scene)
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

### What Changed from v0.5.2

1. **Duration field added** — `duration` field in LUSID scene ensures renderer uses authoritative ADM duration
2. **Fixed truncated renders** — Prevents compositions from being cut short when keyframes end before ADM duration
3. **ADM metadata preservation** — Duration extracted from ADM `<Duration>` field, not calculated from WAV lengths

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
- **⚠️ DEV FLAG:** LFE is currently detected by hardcoded channel index (4th DirectSpeaker). Future update should detect by `speakerLabel` containing "LFE". See `_DEV_LFE_HARDCODED` flag in `xml_etree_parser.py`.

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

## 📄 LUSID Scene JSON Format (v0.5.2)

```json
{
  "version": "0.5",
  "sampleRate": 48000,
  "timeUnit": "seconds",
  "duration": 566.0,
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

### Top-Level Fields

- **version**: LUSID format version (currently "0.5")
- **sampleRate**: Sample rate in Hz (must match audio files)
- **timeUnit**: Time unit for keyframes: `"seconds"` (default), `"samples"`, or `"milliseconds"`
- **duration**: **NEW in v0.5.2** - Total scene duration in seconds (from ADM metadata). Ensures renderer uses authoritative ADM duration instead of calculating from WAV file lengths.
- **metadata**: Optional metadata object (source format, original duration string, etc.)
- **frames**: Array of time-ordered frames containing spatial nodes

---

## 🔗 Source ↔ Audio File Mapping

### Node ID → WAV Filename

The stem splitter and renderer use node group IDs for file matching:

| Node ID | WAV File   | Description           |
| ------- | ---------- | --------------------- |
| `1.1`   | `1.1.wav`  | DirectSpeaker Left    |
| `4.1`   | `LFE.wav`  | LFE (special case)    |
| `11.1`  | `11.1.wav` | Audio object group 11 |

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
    xml_etree_parser.py          # NEW: ADM XML → LUSID scene (direct parsing)
    __init__.py                # Updated: exports xmlParser + DirectSpeakerNode

spatial_engine/src/
    JSONLoader.cpp             # NEW: reads LUSID scene format
    JSONLoader.hpp             # NEW: updated SpatialData for LUSID
```

---

## ⚠️ Developer Notes & Flags

### Python Virtual Environment

**Important:** The sonoPleth project uses a Python virtual environment located at the **project root** (`sonoPleth/bin/`). Always use `python` (not `python3`) when running commands from the project root to ensure you're using the venv Python with all dependencies (including `lxml`, `soundfile`, etc.):

```bash
# From sonoPleth project root:
python LUSID/tests/benchmark_xml_parsers.py   # ✅ uses venv
python3 LUSID/tests/benchmark_xml_parsers.py  # ❌ uses system Python, missing lxml
```

### `_DEV_LFE_HARDCODED` (in xml_etree_parser.py)

LFE detection currently uses hardcoded index (4th DirectSpeaker channel). Set this flag to `False` when implementing speaker-label-based detection (`"LFE" in speakerLabel`).

### XML Parsing Dependency Decision — ✅ RESOLVED (2026-02-10)

**Decision: Option B — `xml.etree.ElementTree` (stdlib only)**

`LUSID/src/xml_etree_parser.py` now parses ADM XML directly using Python stdlib. No external dependencies required. Benchmarked against `lxml` — see `LUSID/internalDocs/xml_benchmark.md`:

- **2.3x faster** than the old lxml two-step pipeline (547 ms vs 1253 ms on 25 MB XML)
- **5.5x more memory** (175 MB vs 32 MB) — acceptable for typical ADM files
- **Output parity** — produces identical LUSID scenes
- The old dict-based `xmlParser.py` + `adm_to_lusid_scene()` path has been archived in `old_XML_parse/` for reference

### Intermediate Data Files — ✅ ELIMINATED (2026-02-10)

The pipeline no longer writes `objectData.json`, `directSpeakerData.json`, or `globalData.json` as intermediate files. Parsed dicts flow directly in memory from `parseMetadata()` → `packageForRender()` → `adm_to_lusid_scene()`. The `containsAudio.json` is still written to disk (consumed by `splitStems.py`).

`load_processed_data_and_build_scene()` is archived in `old_XML_parse/xmlParser.py` and is no longer used by the main pipeline.

**TODO:** Create a debug/print summary function that works from the `LusidScene` object directly, replacing the old `analyzeMetadata.printSummary()` which required `objectData.json` on disk.

### ⚠️ Duration Field Issue — Speaker Layout Dependent (2026-02-16)

**Issue:** Although LUSID correctly exports duration (566 seconds from ADM metadata), the C++ renderer still produces shortened output files when using the **allosphere speaker layout (56 channels)**, but renders correctly with the **translab config (18 channels)**.

**Symptoms:**

- LUSID scene shows: `"duration": 566.0` ✅
- Transl ab layout (18 chan): Renders full 566 seconds ✅
- Allosphere layout (56 chan): Renders truncated duration ❌

**Hypothesis:** Memory/buffer allocation issue in C++ renderer when handling high channel counts (56 vs 18 speakers). Duration logic may be affected by speaker layout initialization or buffer sizing.

**Status:** Documented for investigation. Do not investigate now — focus on core duration preservation logic first.

**Investigation Context Window:**

- Compare renderer output logs between translab (18 chan) and allosphere (56 chan) layouts
- Check for memory allocation differences in `SpatialRenderer::init()`
- Verify duration calculation doesn't depend on speaker count
- Test with intermediate channel counts (24, 32, 48) to find threshold
- Examine buffer allocation in `VBAPRenderer` vs `SpatialRenderer`

---

## Testing

```bash
# Run all LUSID tests (106 tests)
cd LUSID && python3 -m unittest discover -s tests -v

# Tests cover:
# - DirectSpeakerNode data model
# - Parser handling of direct_speaker type
# - xmlParser: ADM dicts → LUSID scene conversion
# - xml_etree_parser: stdlib XML → LUSID scene (36 tests)
# - LFE detection (hardcoded + future label-based)
# - Node ID → source name mapping
# - Silent channel skipping
# - Standalone EBU XML parsing (no bwfmetaedit wrapper)
# - Round-trip: parse → write → re-parse
# - All existing node types (audio_object, spectral_features, agent_state)

# Run benchmark (requires venv Python with lxml)
cd sonoPleth_root && python LUSID/tests/benchmark_xml_parsers.py
```

---

## ✅ v0.5.2 Implementation Status (2026-02-13)

### What Was Done This Session

**LUSID core (70 tests, all passing):**

- `DirectSpeakerNode` added to `scene.py` (type=`direct_speaker`, cart, speakerLabel, channelID)
- `parser.py` updated with `_parse_direct_speaker()` + validation (missing/NaN cart)
- `xml_etree_parser.py` created — `parse_adm_xml_to_lusid_scene()` parses ADM XML directly → LUSID scene
- `__init__.py` exports updated (transcoder → xmlParser)
- JSON schema updated with `direct_speaker` type
- `test_parser.py` — 42 tests (DirectSpeaker model, parsing, fixture)
- `test_xml_etree_parser.py` — 36 tests (timecodes, LFE, mixed scenes, silent channels, round-trip, file I/O)
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
- `LUSID/README.md` — rewritten for v0.5.2
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

## ✅ v0.5.2 Implementation Status (2026-02-10)

### What Was Done This Session

**Eliminate intermediate JSON files:**

- `src/analyzeADM/parser.py` — `parseMetadata()` returns `{'objectData', 'globalData', 'directSpeakerData'}` dict; `getGlobalData()` / `getDirectSpeakerData()` accept `outputPath=None`
- `src/packageADM/packageForRender.py` — accepts `parsed_adm_data` and `contains_audio_data` dicts directly, calls `adm_to_lusid_scene()` in memory
- `runPipeline.py` — dicts flow: `channelHasAudio()` → `parseMetadata()` → `packageForRender()` with no JSON intermediates
- `runGUI.py` — same dict-based flow

**xml.etree.ElementTree parser (stdlib, zero dependencies):**

- `LUSID/src/xml_etree_parser.py` — `parse_adm_xml_to_lusid_scene(xml_path)` end-to-end XML → LUSID scene
  - Handles both bwfmetaedit conformance-point XML and standalone EBU ADM XML
  - Extracts `<Technical>` global data, DirectSpeakers, Objects, LFE
  - Silent channel skipping via `contains_audio` dict
- `LUSID/src/__init__.py` — exports `parse_adm_xml_to_lusid_scene`, `parse_and_write_lusid_scene`
- `LUSID/tests/test_xml_etree_parser.py` — 36 tests (all passing)
- `LUSID/tests/benchmark_xml_parsers.py` — performance comparison script

**Benchmark results (25.1 MB XML, 5348 frames, 56 objects):**

- etree: 547 ms parse, 175 MB peak memory
- lxml (old two-step): 1253 ms parse, 32 MB peak memory
- etree is 2.3x faster, 5.5x more memory — acceptable trade-off
- Output parity confirmed ✅

**Duration field implementation (v0.5.2):**

- `LUSID/src/scene.py` — Added `duration: float = -1.0` to `LusidScene` dataclass
- `LUSID/src/xml_etree_parser.py` — Extracts ADM `<Duration>` field (e.g., "00:09:26.000" → 566.0 seconds)
- `LUSID/schema/lusid_scene_v0.5.schema.json` — Added optional `duration` field (number, minimum 0)
- `spatial_engine/src/JSONLoader.hpp` — Added `double duration = -1.0` to `SpatialData` struct
- `spatial_engine/src/JSONLoader.cpp` — Parses `duration` field from LUSID JSON
- `spatial_engine/src/renderer/SpatialRenderer.cpp` — Prioritizes LUSID duration over WAV length calculation
- `spatial_engine/src/vbap_src/VBAPRenderer.cpp` — Same duration logic as SpatialRenderer
- Tested: 9:26 ADM composition now renders full 566 seconds instead of stopping at 2:47 (319 seconds)

**Documentation:**

- `LUSID/internalDocs/xml_benchmark.md` — full benchmark report
- `LUSID/internalDocs/AGENTS.md` — this file, updated with venv note and session results

**Total LUSID tests: 106 (all passing)**

---

## 🎯 Next Steps

### ✅ Completed

- [x] **Clean up `splitStems.py` output path** — Fixed hardcoded path to use `output_dir` parameter correctly (Feb 10, 2026)

- [x] **Eliminate intermediate JSON files** — `parseMetadata()` now returns dicts directly; `packageForRender()` passes them in-memory to `adm_to_lusid_scene()`. No more `objectData.json`, `directSpeakerData.json`, `globalData.json` written to disk. (Feb 10, 2026)

- [x] **xml.etree.ElementTree migration** — Created `LUSID/src/xml_etree_parser.py` with `parse_adm_xml_to_lusid_scene()`. Stdlib-only, zero dependencies, 2.3x faster than old lxml two-step pipeline. 36 tests passing. Benchmarked in `xml_benchmark.md`. (Feb 10, 2026)

- [x] **XML parser performance benchmarking** — Documented in `LUSID/internalDocs/xml_benchmark.md`. etree: 547ms/175MB, lxml: 1253ms/32MB on 25MB XML. Output parity confirmed. (Feb 10, 2026)

- [x] **Duration field implementation** — Added `duration` field to LUSID scene schema, ADM duration extraction, C++ renderer updates to prioritize LUSID duration over WAV length. Prevents truncated renders. (Feb 13, 2026)

### Priority 1 — Ready for Implementation

- [ ] **Create LUSID scene debug/summary function** — Replace the old `analyzeMetadata.printSummary()` (which reads from disk) with a function that prints a summary directly from a `LusidScene` object.

- [ ] **Wire `xml_etree_parser` into main pipeline** — Replace the sonoPleth `parseMetadata()` → LUSID `adm_to_lusid_scene()` two-step flow with a single call to `parse_adm_xml_to_lusid_scene()` in `packageForRender.py`. This makes the pipeline XML → LUSID scene in one step.

- [ ] **Implement proper LFE detection** — Replace hardcoded channel index (4th DirectSpeaker) with speaker label matching (`"LFE" in speakerLabel`). Update `_DEV_LFE_HARDCODED` flag to `False` and implement label-based detection in `xml_etree_parser.py`.

### Future — Deferred

- [ ] **Version bump to v0.6.0** — Reflect significant performance improvements (2.3x faster XML parsing, stdlib-only XML processing, eliminated intermediate JSON I/O) and architectural milestone (LUSID as canonical format)

- [ ] **Reorganize LUSID transcoding** — Move all parsing and transcoding utilities into `LUSID/transcoding/` directory for better organization. Deferred until the current module structure causes actual friction. See proposed structure in "Detailed Analysis" section below.

### Detailed Analysis for Next Context Window

#### Task: Eliminate Intermediate JSON Files — ✅ DONE

Implemented Feb 10, 2026. See files changed:

- `src/analyzeADM/parser.py` — `parseMetadata()` returns dict with `objectData`, `globalData`, `directSpeakerData` keys; `getGlobalData()` and `getDirectSpeakerData()` accept `outputPath=None` to skip disk write
- `src/packageADM/packageForRender.py` — accepts `parsed_adm_data` and `contains_audio_data` dicts directly
- `runPipeline.py` — wires dicts through: `parseMetadata()` → `packageForRender()` → `adm_to_lusid_scene()`
- `runGUI.py` — same dict-based flow

#### Task: xml.etree.ElementTree Migration — ✅ DONE

Implemented Feb 10, 2026. See:

- `LUSID/src/xml_etree_parser.py` — `parse_adm_xml_to_lusid_scene(xml_path)` end-to-end
- `LUSID/tests/test_xml_etree_parser.py` — 36 tests
- `LUSID/tests/benchmark_xml_parsers.py` — performance comparison
- `LUSID/internalDocs/xml_benchmark.md` — benchmark results

#### Task: Reorganize LUSID Transcoding Structure

**Current Structure:**

```
LUSID/src/
    parser.py      # LUSID scene parsing
    xml_etree_parser.py   # ADM XML → LUSID conversion (direct parsing)
    scene.py       # Node models
```

**Proposed Structure:**

```
LUSID/transcoding/
    __init__.py
    adm/
        xml_etree_parser.py    # New: stdlib XML parser
        xml_lxml_parser.py     # Current: lxml-based parser
        adm_to_lusid.py        # ADM → LUSID conversion logic
    core/
        scene.py               # Node models (moved)
        parser.py              # LUSID scene parsing (moved)
    utils/
        benchmarks.py          # Performance testing utilities

LUSID/src/  # Kept for backward compatibility
    __init__.py               # Re-exports from transcoding/
```

**Benefits:**

- Clear separation of transcoding vs core LUSID functionality
- Easy A/B testing of XML parsers
- Better organization for external usage of LUSID module
- Maintains backward compatibility

#### Performance Benchmarking Plan

**Test Scenarios:**

1. **Small ADM file** (~100 frames, few objects)
2. **Medium ADM file** (~1000 frames, mixed bed/objects)
3. **Large ADM file** (`SWALE-ATMOS-LFE.wav`: 2823 frames, 24 sources)
4. **Stress test** (synthetic 10000+ frames)

**Metrics to Measure:**

- Parse time (XML → Python dicts)
- Peak memory usage
- Dict conversion time (parsed data → LUSID scene)
- Total pipeline time

**Benchmark Output Format** (for `xml_benchmark.md`):

```markdown
| Test File | Parser | Parse Time | Memory Peak | Dict→LUSID | Total |
| --------- | ------ | ---------- | ----------- | ---------- | ----- |
| small.xml | lxml   | 5ms        | 12MB        | 2ms        | 7ms   |
| small.xml | etree  | 8ms        | 8MB         | 2ms        | 10ms  |
```

### Ready for Next Context Window

All analysis complete. Current state:

1. **Split stems**: ✅ Complete
2. **Eliminate intermediate JSONs**: ✅ Complete (Feb 10)
3. **XML parser migration**: ✅ Complete — `xml_etree_parser.py` created, benchmarked (Feb 10)
4. **Performance testing**: ✅ Complete — results in `xml_benchmark.md` (Feb 10)
5. **Reorganization**: Deferred — structure planned but not yet needed

**Next Session Goals:**

1. Wire `xml_etree_parser.parse_adm_xml_to_lusid_scene()` into main pipeline (single-step XML → LUSID)
2. Create LUSID scene debug/summary print function
3. Evaluate if sonoPleth's `lxml` dependency can be fully removed

### Future tasks

- [ ] **Additional node types** — `reverb_zone`, `interpolation_hint`, etc.
- [ ] **Performance optimization** — optimize for large scenes (1000+ frames). Current: 2823 frames loads in <1ms

---

## Archival Plan: XML Parser Migration

### Overview

As part of the XML parsing optimization, we're migrating from the two-step lxml pipeline (XML → dicts → JSON → LUSID) to a single-step stdlib xml.etree.ElementTree parser. This eliminates intermediate JSON I/O and reduces dependencies.

**Decision:** Adopt `xml.etree.ElementTree` (stdlib) for LUSID's XML parsing. Benchmark shows 2.3x faster than lxml pipeline with acceptable memory trade-off (5.5x more memory, but ADM XML is ≤100MB).

### Archival Procedure

1. **Create archival directories** under `LUSID/src/old_XML_parse/` and `LUSID/tests/old_XML_parse/`
2. **Move obsolete files** with explanatory header comments
3. **Update imports** in remaining files to use new `xml_etree_parser.py`
4. **Add cross-references** in documentation to archived files
5. **Run full test suite** to ensure no regressions

### Files to Archive

| Original Location                               | Archive Location                                   | Reason                                                    | Header Comment                                                                                                                                        |
| ----------------------------------------------- | -------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LUSID/src/xmlParser.py`                        | `LUSID/src/old_XML_parse/xmlParser.py`             | Replaced by `xml_etree_parser.py` (single-step XML→LUSID) | `# ARCHIVED: Two-step dict-based parser. Replaced by xml_etree_parser.py for single-step XML parsing. See LUSID/internalDocs/AGENTS.md#archival-plan` |
| `LUSID/tests/test_xmlParser.py`                 | `LUSID/tests/old_XML_parse/test_xmlParser.py`      | Tests for obsolete dict-based parser                      | `# ARCHIVED: Tests for old xmlParser.py. New tests in test_xml_etree_parser.py. See LUSID/internalDocs/AGENTS.md#archival-plan`                       |
| `src/analyzeADM/parser.py` (modified)           | `src/analyzeADM/old_XML_parse/parser.py`           | lxml-based parsing functions replaced by stdlib           | `# ARCHIVED: lxml parseMetadata() replaced by xml_etree_parser.parse_adm_xml_to_lusid_scene(). See LUSID/internalDocs/AGENTS.md#archival-plan`        |
| `src/packageADM/packageForRender.py` (modified) | `src/packageADM/old_XML_parse/packageForRender.py` | Dict-passing version replaced by direct XML               | `# ARCHIVED: Dict intermediary eliminated. Now calls xml_etree_parser directly. See LUSID/internalDocs/AGENTS.md#archival-plan`                       |
| `runPipeline.py` (modified)                     | `old_XML_parse/runPipeline.py`                     | JSON I/O eliminated, dicts flow in memory                 | `# ARCHIVED: Intermediate JSON files removed. Pipeline now XML→LUSID directly. See LUSID/internalDocs/AGENTS.md#archival-plan`                        |
| `runGUI.py` (modified)                          | `old_XML_parse/runGUI.py`                          | Same pipeline changes as runPipeline.py                   | `# ARCHIVED: GUI pipeline updated to match runPipeline.py changes. See LUSID/internalDocs/AGENTS.md#archival-plan`                                    |

### Integration Status & Implementation Plan

#### ✅ **Completed Tasks**

- ✅ **Created** `xml_etree_parser.py` (stdlib XML parser)
- ✅ **Benchmarked** vs lxml (2.3x faster, output parity confirmed)
- ✅ **Added tests** (36 new tests, 106 total passing)
- ✅ **Updated pipeline** to pass dicts in memory (no JSON I/O)
- ✅ **Documented archival plan** with detailed procedures
- ✅ **Task 1: Archive obsolete XML parsing files** - Moved `xmlParser.py` and `test_xmlParser.py` to `old_XML_parse/` with headers, updated `__init__.py`, all 78 tests pass
- ✅ **Task 2: Integrate xml_etree_parser into Main Pipeline** - Modified `runPipeline.py` and `runGUI.py` to use single-step XML→LUSID, updated `packageForRender.py` to accept `LusidScene` objects directly, all tests pass
- ✅ **Task 3: Create LusidScene Summary Debug Method** - Added `summary()` method to `LusidScene` class, integrated into `runPipeline.py` and `runGUI.py`, tested with real ADM data
- ✅ **Task 4: Update splitStems for In-Memory Dicts** - Modified `splitChannelsToMono()` to accept optional `contains_audio_data` parameter, updated `packageForRender.py` to pass data directly, maintains backward compatibility
- ✅ **Task 5: Evaluate Full lxml Removal** - No remaining lxml imports in active codebase, `src/analyzeADM/parser.py` archived, `lxml` can be removed from `requirements.txt`

## ✅ **XML Parser Migration Complete**

**Migration Summary:**

- **Performance**: 2.3x faster XML parsing with stdlib `xml.etree.ElementTree`
- **Memory**: 5.5x more memory usage (acceptable for ADM XML ≤100MB)
- **Dependencies**: Eliminated `lxml` dependency from active codebase
- **Architecture**: Single-step XML→LUSID pipeline (no intermediate JSONs/dicts)
- **Testing**: All 78 LUSID tests pass, output parity confirmed
- **Archival**: Obsolete files preserved in `old_XML_parse/` subdirectories

**Files Archived:**

- `LUSID/src/xmlParser.py` → `LUSID/src/old_XML_parse/xmlParser.py`
- `LUSID/tests/test_xmlParser.py` → `LUSID/tests/old_XML_parse/test_xmlParser.py`
- `src/analyzeADM/parser.py` → `src/analyzeADM/old_XML_parse/parser.py`

**Next Steps:**

- Consider removing `lxml` from `requirements.txt` (tested: no active usage)
- Reorganize LUSID directory structure if desired
- Performance optimizations for large scenes (1000+ frames)

- Create `LUSID/src/old_XML_parse/` and `LUSID/tests/old_XML_parse/` directories
- Move `xmlParser.py` and `test_xmlParser.py` with header comments
- Update `LUSID/src/__init__.py` to remove old exports
- Run full test suite (106 tests) to ensure no regressions

**Task 2: Integrate xml_etree_parser into Main Pipeline (30 min)**

- Modify `runPipeline.py`: Replace `parseMetadata()` → `xml_etree_parser.parse_adm_xml_to_lusid_scene()`
- Modify `packageForRender.py`: Accept `LusidScene` object directly instead of dicts
- Test end-to-end pipeline produces identical `scene.lusid.json`

**Task 3: Create LusidScene Summary Debug Method (20 min)**

- Add `summary()` method to `LusidScene` class in `scene.py`
- Print version, sampleRate, timeUnit, frame count, node counts by type
- Update `runPipeline.py` to call `scene.summary()` instead of old printSummary

**Task 4: Update splitStems for In-Memory Dicts (25 min)**

- Modify `splitChannelsToMono()` to accept `contains_audio_data` parameter
- Update `mapEmptyChannels()` for in-memory dict format
- Pass dict from `runPipeline.py` → `packageForRender.py` → `splitStems.py`
- Maintain backward compatibility (read JSON if dict not provided)

**Task 5: Evaluate Full lxml Removal (10 min)**

- Search codebase for remaining `lxml` imports/usages
- Check if other components still depend on lxml
- Document lxml removal in requirements if safe
- Test pipeline works after potential removal

#### 📋 **Risk Assessment & Safety**

- **Low Risk**: All changes maintain backward compatibility, comprehensive tests
- **Safety**: Run test suite after each task, keep archived files for rollback
- **Validation**: Output parity confirmed at each step, git tracking for changes
- **Timeline**: ~1.5-2 hours total implementation time
