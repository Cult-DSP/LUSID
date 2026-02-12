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
