# CHANGELOG_TOOLCHAIN.md — Cult DSP Toolchain (contract-only)

**Canonical location:** `LUSID/internalDocsMD/CHANGELOG_TOOLCHAIN.md`  
**Scope:** changes that affect cross-repo data flow/contracts across LUSID ⇄ sonoPleth ⇄ SpatialSeed

---

## Rules (agents MUST follow)

### What belongs here
Only changes that affect toolchain contracts, including:
- LUSID schema version bumps
- new/removed/renamed fields or semantic changes in `scene.lusid.json`
- new node types consumed by renderer/exporter (or changes to ignore behavior)
- LUSID package layout changes (required files, naming, locations)
- ID ↔ WAV mapping changes (including LFE filename special-case)
- ADM/BW64 ordering or container requirements (`axml`, `chna`, channel order)
- toolchain flags added/removed/defaults changed (`LUSID/config/toolchain_flags.json`)
- validation rules that change pipeline pass/fail behavior
- golden fixture spec changes

### Required update triggers
Agents MUST add an entry whenever:
- a change is “toolchain-relevant” per `LUSID/internalDocsMD/AGENTS.md`
- any toolchain flag key or default changes
- golden fixture spec changes
- consumer repos must update their LUSID submodule pin to remain compatible

### Entry format (required)
Each entry MUST include:
- date (YYYY-MM-DD)
- change summary
- why
- compatibility impact (patch-safe vs breaking)
- required follow-up tasks for:
  - sonoPleth
  - SpatialSeed
- fixture impact (updated / no change)
- migration notes (if any)

---

## Template (copy/paste for new entries)

### YYYY-MM-DD — <Short title>
**Summary**
- <bullet 1>
- <bullet 2>

**Why**
- <reason>

**Compatibility**
- Type: patch-safe / breaking
- Schema version: <old> → <new> (if applicable)

**Flags**
- Added/changed defaults:
  - <flag_key>: <old> → <new>

**Required follow-up**
- sonoPleth:
  - <task list>
- SpatialSeed:
  - <task list>

**Fixture impact**
- updated / no change
- Notes: <if updated, what changed>

**Migration notes**
- <steps, if any>

---

## Initial baseline (fill tomorrow after folders/assets exist)

### 2026-02-11 — Baseline toolchain contract (v0.5.2)
**Summary**
- Establish canonical toolchain contract docs (AGENTS + changelog)
- Establish canonical toolchain flags location and defaults
- Establish golden fixture folder and validation gates

**Why**
- Prevent contract drift across three repos while scaling experiments rapidly

**Compatibility**
- Type: patch-safe
- Schema version: 0.5.2

**Flags**
- Defaults recorded in `LUSID/config/toolchain_flags.json`

**Required follow-up**
- sonoPleth:
  - Pin LUSID submodule to baseline commit
  - Confirm loader + WAV mapping + LFE behavior on golden fixture
- SpatialSeed:
  - Pin LUSID submodule to baseline commit
  - Confirm package writer + ADM export ordering on golden fixture

**Fixture impact**
- updated
- Notes: create `LUSID/fixtures/golden_package_v0.5.2/` with minimal 48k mono WAVs + JSON

**Migration notes**
- none

### 2026-02-11 — XML parser migration and intermediate JSON elimination
**Summary**
- Migrated ADM XML parsing from lxml to Python stdlib (xml.etree.ElementTree)
- Eliminated intermediate JSON files (objectData.json, directSpeakerData.json, globalData.json)
- Data flows as Python dicts in memory from parseMetadata() → adm_to_lusid_scene()
- Added xml_etree_parser.py for single-step ADM XML → LUSID scene conversion
- Performance: 2.3x faster, 5.5x more memory usage (acceptable for typical ADM files)

**Why**
- Reduce external dependencies (lxml no longer required for active LUSID code)
- Simplify pipeline by eliminating disk I/O for intermediate dicts
- Improve performance for large XML files

**Compatibility**
- Type: patch-safe
- Schema version: 0.5.1 → 0.5.2

**Flags**
- Added/changed defaults: none

**Required follow-up**
- sonoPleth:
  - Wire xml_etree_parser into main pipeline (replace lxml two-step with single stdlib step)
  - Update packageForRender.py to call stdlib parser directly
  - Test end-to-end equivalence with existing lxml pathway
- SpatialSeed:
  - No changes required (export unaffected)

**Fixture impact**
- no change

**Migration notes**
- lxml pathway preserved in old_XML_parse/ for fallback if needed

### 2026-02-11 — LUSID package ingestion pipeline
**Summary**
- Added createFromLUSID.py script for direct ingestion of LUSID packages
- Pipeline: LUSID package → C++ spatial renderer (reads LUSID scene directly)
- Supports spatializers: DBAP, VBAP, LBAP
- Includes optional render analysis PDF generation
- Added importingLUSIDpackage.md spec defining package layout, audio resolution, validation rules

**Why**
- Enable sonoPleth to consume LUSID packages produced by SpatialSeed
- Establish toolchain contract for cross-repo data flow
- Provide CLI interface for LUSID-based workflows

**Compatibility**
- Type: patch-safe
- Schema version: 0.5.2

**Flags**
- Added/changed defaults: none

**Required follow-up**
- sonoPleth:
  - Integrate package validation per importingLUSIDpackage.md rules
  - Test with golden fixture package
- SpatialSeed:
  - Ensure packages conform to importingLUSIDpackage.md spec
  - Update package writer to include required files (scene.lusid.json, containsAudio.json, mir_summary.json)

**Fixture impact**
- no change (fixture to be created)

**Migration notes**
- Existing ADM BWF pipeline unchanged; LUSID package ingestion is additional capability
