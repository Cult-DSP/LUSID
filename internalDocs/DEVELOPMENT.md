# LUSID Scene v0.5.2 — Archival Development History

**Internal archival notes for the LUSID scene specification**  
**Last Updated:** April 27, 2026

---

## Scope (Current State)

LUSID is a **spec-only** repository: documentation, schema, and templates. No runtime code, pipelines, loaders, or parsers live here. All runtime behavior is owned by external components (for example, `cult-transcoder` and the spatialroot renderer).

This file preserves historical implementation notes that are **no longer active** in this repo but may be useful for context.

---

## Historical Milestones (Archived)

### v0.5.2 Format Expansion

- Added `direct_speaker` node type to represent fixed bed channels.
- Established the `X.Y` node ID convention (group/level).
- Introduced optional `duration` at the top level to preserve ADM duration.

### XML Migration (Historical)

- Replaced a two-step XML pipeline (XML → dicts → JSON → LUSID) with a direct XML → LUSID conversion.
- Evaluated stdlib `xml.etree.ElementTree` for faster parsing with higher memory usage.
- Archived lxml/dict-based parsing paths.

### Old Schema Deprecation

- Deprecated `renderInstructions.json` and associated loaders/transcoders.
- Transitioned downstream tools to consume LUSID scenes directly.

---

## Legacy File Moves (Archived References)

These file moves occurred during the runtime transition and are preserved here only as historical notes.

- `LUSID/src/xmlParser.py` → `LUSID/src/old_XML_parse/xmlParser.py`
- `LUSID/tests/test_xmlParser.py` → `LUSID/tests/old_XML_parse/test_xmlParser.py`
- `LUSID/src/transcoder.py` → `LUSID/src/old_schema/transcoder.py`
- `LUSID/tests/test_transcoder.py` → `LUSID/tests/old_schema/test_transcoder.py`

---

## What Is Canonical Now

- Schema: `LUSID/schema/lusid_scene_v0.5.schema.json`
- Spec docs: `LUSID/README.md`
- Agent spec: `LUSID/internalDocs/LUSID_AGENTS.md`

---

## Maintenance Notes

- Keep schema, examples, and docs aligned.
- Avoid documenting runtime behavior here.
- Treat this file as historical context only.
- For design rationale and influences, see `LUSID/internalDocs/DESIGNDOC.md`.
