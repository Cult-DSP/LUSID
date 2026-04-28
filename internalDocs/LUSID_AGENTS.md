## LUSID Agent Specification — Scene v0.5.2 (Spec Only)

**Updated:** 2026-04-27  
**Author:** LUSID / spatialroot Integration Team  
**Purpose:** Agent-level instructions for maintaining the LUSID Scene specification. This repo is **spec-only**: documentation, schema, and templates. All runtime functionality lives elsewhere.

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
- **Semantics:** Spatial audio source with time-varying position.

### `direct_speaker` (type: `"direct_speaker"`)

Fixed-position bed channel mapped to a speaker label.

- **Fields:** `id`, `type`, `cart: [x, y, z]`, `speakerLabel`, `channelID`
- **ID convention:** `X.1` where X = group number (groups 1–10 for standard Atmos bed)
- **Semantics:** Fixed-position bed channel. `speakerLabel` is informational metadata only.

### `LFE` (type: `"LFE"`)

Low-frequency effects — represented without positional data.

- **Fields:** `id`, `type`
- **ID convention:** `X.1`
- **Semantics:** LFE node with no positional data.

### `spectral_features` (type: `"spectral_features"`)

Analysis metadata attached to parent audio_object group.

- **Fields:** `id`, `type`, plus arbitrary data keys (`centroid`, `flux`, `bandwidth`, etc.)
- **ID convention:** `X.2+` (child of group X)
- **Semantics:** Analysis metadata attached to a parent audio_object.

### `agent_state` (type: `"agent_state"`)

AI/agent metadata attached to parent audio_object group.

- **Fields:** `id`, `type`, plus arbitrary data keys (`mood`, `intensity`, etc.)
- **ID convention:** `X.2+` (child of group X)
- **Semantics:** Agent/AI metadata attached to a parent audio_object.

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
- **duration**: **NEW in v0.5.2** - Total scene duration in seconds (from metadata).
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
