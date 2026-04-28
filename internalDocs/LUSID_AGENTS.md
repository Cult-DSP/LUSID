## LUSID Agent Specification — Scene v0.5.2 (Spec Only)

**Updated:** 2026-04-27  
**Author:** LUSID / spatialroot Integration Team  
**Purpose:** Agent-level instructions for maintaining the LUSID Scene specification. This repo is **spec-only**: documentation, schema, and templates. All runtime functionality lives elsewhere (e.g., `cult-transcoder`, spatialroot renderer).

**Scope Requirement:** This repo must not claim runtime functionality. No loaders, parsers, or pipelines live here. Only schema, docs, and templates.

See [internalDocsMD/AGENTS.md](internalDocsMD/AGENTS.md) for repo-wide agent context.

---

## Scope and Non-Goals

- LUSID defines a JSON scene format for spatial audio metadata.
- This repo does not contain any runtime code or tools.
- Do not document runtime behavior (loader behavior, renderer mapping, pipeline steps).

---

## 🏗️ LUSID Node Types

### `audio_object` (type: `"audio_object"`)

Spatial audio source with time-varying Cartesian position.

- **Fields:** `id`, `type`, `cart: [x, y, z]`, optional `gain`
- **ID convention:** `X.1` where X = group number
- **Renderer behavior:** Spatialized via VBAP/DBAP/LBAP

### `direct_speaker` (type: `"direct_speaker"`)

Fixed-position bed channel mapped to a speaker label.

- **Fields:** `id`, `type`, `cart: [x, y, z]`, `speakerLabel`, `channelID`
- **ID convention:** `X.1` where X = group number (groups 1–10 for standard Atmos bed)
- **Renderer behavior:** Treated as an `audio_object` with a single keyframe (static position). The `speakerLabel` field is informational metadata only — the renderer spatializes based on `cart`.

### `LFE` (type: `"LFE"`)

Low-frequency effects — routed directly to subwoofers, not spatialized.

- **Fields:** `id`, `type`
- **ID convention:** `X.1`
- **Renderer behavior:** Bypass spatialization, route to subwoofer channels
- **Renderer behavior:** LFE is routed directly to subwoofers. When sourcing from ADM, LFE maps to channel 4 if the multichannel file has at least 4 channels.

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

## Templates and Examples

Use the JSON example below as the canonical template for the scene format. This repo should not include runtime mapping rules or pipeline instructions.

---

## 📁 File Organization (Spec-Only)

- LUSID schema: [LUSID/schema/lusid_scene_v0.5.schema.json](LUSID/schema/lusid_scene_v0.5.schema.json)
- LUSID docs: [LUSID/README.md](LUSID/README.md)
- Agent spec: [LUSID/internalDocs/LUSID_AGENTS.md](LUSID/internalDocs/LUSID_AGENTS.md)

---

## Maintenance Notes

- Keep the schema and examples in sync.
- Avoid references to runtime behavior or implementation details.
- Use only ASCII characters in schema/examples unless required by the format.

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
