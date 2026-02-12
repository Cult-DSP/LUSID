# AGENTS.md — Cult DSP Toolchain (LUSID ⇄ sonoPleth ⇄ SpatialSeed)

**Canonical location:** `LUSID/internalDocsMD/AGENTS.md`  
**Toolchain config:** `LUSID/config/toolchain_flags.json`  
**Schema version:** `0.5.2`  
**Audience:** autonomous coding agents (not humans)

**Prime directive:** preserve cross-repo contracts while enabling rapid experimentation.

---

## 0) Scope and topology

### 0.1 Repos
- `LUSID/` is the connective tissue and is included as a **git submodule** in:
  - `sonoPleth/` repo
  - `SpatialSeed/` repo

### 0.2 What this file governs
This file defines toolchain-level **contracts** and **governance rules** for data flow across:
- LUSID (schema + transcoders)
- SpatialSeed (authoring + package building + ADM/BW64 container packaging)
- sonoPleth (ADM decode + render; reads LUSID scene directly)

Repo-local `AGENTS.md` files may include operational details, but **MUST NOT contradict** this file.

---

## 1) Source-of-truth and conflict resolution

When any instruction conflicts, resolve in this order:
1) **This file** (toolchain contract authority)
2) LUSID schema + tests (enforcement)
3) SpatialSeed module docs (authoring + packaging)
4) sonoPleth module docs (render pipeline behavior)

Agents MUST NOT “paper over” a contract mismatch by adding a consumer-side workaround.
Fix or version the contract in LUSID first.

---

## 2) Contract artifacts (explicit surface area)

The following are the **only** contract-level artifacts unless this file is updated.

### 2.1 Interchange artifacts
- `scene.lusid.json` (required, schema v0.5.2)
- `containsAudio.json` (required)
- `mir_summary.json` (required)
- mono WAV stems at package root (required)

### 2.2 Toolchain configuration (behavior flags)
- `LUSID/config/toolchain_flags.json` (required, committed)
  - controls prototype-locked behavior and experimental toggles
  - **NO environment variables** in this phase

Agents MUST NOT introduce new required artifacts at package root without updating:
- this file
- golden fixture package
- changelog (CHANGELOG_TOOLCHAIN.md)
- version policy (and bump if needed)

---

## 3) LUSID package folder contract (v1)

### 3.1 Package root layout (no nesting)
A valid LUSID package folder contains the following **at the package root**:

Required files:
- `scene.lusid.json`
- `containsAudio.json`
- `mir_summary.json`

Required mono WAV stems:
- beds: `1.1.wav`, `2.1.wav`, `3.1.wav`, `5.1.wav` … `10.1.wav`
- LFE special: `LFE.wav`
- objects: `11.1.wav`, `12.1.wav`, `13.1.wav`, … (as needed)

Rules:
- Do not nest WAVs under `audio/` in v1.
- Do not reintroduce `src_N.wav` naming.

### 3.2 Node ID ↔ WAV filename mapping (hard contract)
- Default rule: node ID `X.1` loads from `X.1.wav`
- **Exception:** LFE node `4.1` loads from `LFE.wav` (not `4.1.wav`)

This mapping must be consistent across:
- SpatialSeed package writer
- sonoPleth stem splitting and source loading
- renderer WAV loading logic

---

## 4) LUSID scene contract (v0.5.2)

### 4.1 Header (required)
`scene.lusid.json` MUST contain:
- `"version": "0.5.2"`
- `"sampleRate": 48000`
- `"timeUnit": "seconds"`
- `"frames": [...]`

### 4.2 Coordinate system (canonical)
- Normalized Cartesian cube: `x, y, z ∈ [-1, 1]`
- Axes: **+X right, +Y front, +Z up**
- Out-of-range values MUST be clamped; clamp events MUST be logged.

### 4.3 Frames policy
- Frames are time-ordered.
- Delta frames are allowed (frame may contain only changed nodes).
- Mandatory invariant: every spatial source must have an initial keyframe at **t = 0.0**.

### 4.4 Node types (minimum set)
Toolchain compatibility requires these node types:

#### `audio_object`
- required: `id`, `type`, `cart: [x, y, z]`
- optional: `gain`, additional metadata behind flags
- renderer: spatialized (DBAP/VBAP/LBAP)

#### `direct_speaker`
- required: `id`, `type`, `cart: [x, y, z]`, `speakerLabel`, `channelID`
- renderer: treated as static spatial source (single keyframe at t=0)

#### `LFE`
- required: `id`, `type`
- renderer: bypass spatialization; route to subwoofers

#### Optional / ignorable (default)
- `spectral_features`
- `agent_state`

---

## 5) Locked prototype policy (beds + LFE) + controlled escape hatches

### 5.1 Prototype defaults (locked behavior)
By default (prototype v1):
- Beds/direct-speaker groups **1–10** are always included in the LUSID scene.
- LFE is always included as:
  - scene node: `{"id":"4.1","type":"LFE"}`
  - audio file: `LFE.wav`
- In SpatialSeed v1, bed WAVs and `LFE.wav` are typically silent placeholders unless explicitly enabled.

### 5.2 Toolchain flags (canonical shared config; NO env vars)
All behavior toggles MUST be represented in:
- `LUSID/config/toolchain_flags.json`

Agents MUST:
- read flags from this exact path (relative to LUSID submodule root)
- log a one-line resolved flag map at startup in both repos
- treat flags as behavior toggles (no silent schema meaning changes)

#### Canonical flags (toolchain-wide)
- `beds_always_included` (bool)
- `bed_wavs_allow_audio` (bool)
- `lfe_special_case_filename` (bool)
- `lfe_detection_mode` (enum: `"HARDCODED_INDEX" | "LABEL_MATCH"`)
- `adm_export_enabled` (bool)
- `adm_export_include_beds` (bool)

#### Default `toolchain_flags.json` (prototype-safe)
```json
{
  "beds_always_included": true,
  "bed_wavs_allow_audio": false,
  "lfe_special_case_filename": true,
  "lfe_detection_mode": "HARDCODED_INDEX",
  "adm_export_enabled": true,
  "adm_export_include_beds": true
}
```

---

## 6) ADM/BW64 export contract (required)

### 6.1 Output artifacts
When ADM export is enabled:
- `export.adm.wav` (BW64 with ADM metadata embedded)
- optional: `export.adm.xml` sidecar (debug)

### 6.2 Channel ordering (non-negotiable)
BW64 channel order MUST be:
1) beds: `1.1`, `2.1`, `3.1`, `LFE`, `5.1` … `10.1`
2) objects: `11.1`, `12.1`, `13.1`, …

Rules:
- beds first, then objects, always include beds (prototype requirement)
- `containsAudio.json` MUST correspond to this same ordering

### 6.3 Container requirements
ADM export MUST:
- embed `axml` and `chna`
- keep `containsAudio.json` consistent with the exact channel ordering used for packaging
- log the final channel list explicitly

---

## 7) Determinism rules (required for reproducible experiments)

### 7.1 Stable ordering
- stable ordering for source IDs
- stable ordering for JSON serialization outputs (or stable serializer settings)

### 7.2 Randomness policy
Any randomness MUST:
- accept an explicit seed
- record the seed in `mir_summary.json` (or a standardized scene header field if adopted later)
- produce identical outputs given identical inputs + seed + flags

---

## 8) Atomic export rules (avoid half-valid outputs)

Any code path that writes a package or export MUST:
- write into a temp directory
- validate the temp output (Section 9)
- rename/move atomically into final destination

Agents MUST NOT leave partially-written packages as “successful” output.

---

## 9) Toolchain validation (mandatory gates)

A validation routine MUST exist (preferably in LUSID) and be called:
- after package generation (SpatialSeed)
- before rendering (sonoPleth)
- before ADM export

Validation MUST check:
- required root files exist
- all WAVs exist for referenced sources
- sample rate is 48k for all WAVs
- all sources have `t = 0.0` keyframe
- coords are finite; clamp policy applied (log required)
- bed/LFE policy consistent with flags
- `containsAudio.json` channel list consistent with ADM packaging order

Validation failures MUST be fatal.

---

## 10) Consumer robustness rules (to scale experimentation)

### 10.1 Unknown fields/types policy (MUST NOT break experimentation)
Consumers MUST:
- ignore unknown top-level fields safely
- ignore unknown node types safely by default
- log “ignored unknown type” once per type (not per node)

Consumers MUST NOT crash solely due to unknown metadata.

### 10.2 No silent fallbacks
If a required contract element is missing, fail fast with explicit error:
- missing referenced WAV: fatal
- missing `t = 0` keyframe for a source: fatal
- out-of-range coord: recoverable by clamp (log required)
- unknown node type: recoverable ignore (log once per type)

---

## 11) Flag governance rules (prevent flag sprawl)

Agents MUST:
- put any toolchain-relevant behavior toggle into `LUSID/config/toolchain_flags.json`
- document any new key or semantics change in this file
- add defaults in `toolchain_flags.json` in the same PR

Agents MUST NOT:
- add ad-hoc “DEV_…” booleans scattered across repos
- add hidden “magic behavior” without a documented flag and logs

---

## 12) Golden fixture package (contract enforcement)

### 12.1 Fixture purpose
The golden fixture is a minimal LUSID package used to:
- prevent silent contract drift
- provide a universal smoke-test input across SpatialSeed and sonoPleth
- enforce flag + ordering rules
- ensure LFE and bed handling stays consistent

### 12.2 Fixture location (canonical)
`LUSID/fixtures/golden_package_v0.5.2/`

### 12.3 Golden fixture spec (must match contract)
The fixture folder MUST contain these files at root:

**Required JSON:**
- `scene.lusid.json`
- `containsAudio.json`
- `mir_summary.json`

**Required WAVs (mono, 48k):**
- beds: `1.1.wav`, `2.1.wav`, `3.1.wav`, `5.1.wav`
- LFE: `LFE.wav`
- objects: `11.1.wav`, `12.1.wav`

**WAV constraints:**
- sample rate: 48000
- channels: mono
- duration: ≥ 0.25 s (short is fine)
- content: may be silence or test tones (keep deterministic)

**Scene constraints:**
- `"version": "0.5.2"`, `"sampleRate": 48000`, `"timeUnit": "seconds"`
- frames MUST include `t = 0.0` for each source that appears in the fixture:
  - direct speakers: `1.1`, `2.1`, `3.1`, `5.1`
  - objects: `11.1`, `12.1`
- coordinate system matches canonical (+Y front, +Z up) with values in range

**LFE constraints:**
- include node: `{"id":"4.1","type":"LFE"}`
- LFE audio filename MUST be `LFE.wav`

**containsAudio.json constraints:**
- MUST correspond to ADM/BW64 channel ordering rules (beds first, then objects)
- MUST list/encode channels consistently with the fixture’s intended export list

### 12.4 Fixture test gates (required)
Any contract-relevant change MUST ensure:
- SpatialSeed can generate a package matching this spec and passes validation
- sonoPleth can load and render the fixture package
- ADM export can package a valid BW64 with the correct channel ordering (if enabled)

---

## 13) Toolchain changelog (contract-only)

### 13.1 Changelog location (canonical)
`LUSID/internalDocsMD/CHANGELOG_TOOLCHAIN.md`

### 13.2 What belongs in the toolchain changelog
Only changes that affect cross-repo data flow or contracts, including:
- schema version bumps
- new/removed/renamed fields or semantic changes
- new node types consumed by renderer/exporter
- package layout changes
- ID ↔ WAV mapping changes (including LFE behavior)
- ADM/BW64 ordering or container requirements
- toolchain flags added/removed/defaults changed
- validation rules that affect pipeline pass/fail

### 13.3 Mandatory update triggers
Agents MUST add a changelog entry whenever:
- a change is “toolchain-relevant” (see Section 15)
- a flag key or default changes
- the golden fixture spec changes
- any consumer repo must update its pinned LUSID commit to remain compatible

### 13.4 Entry format (required)
Each entry MUST include:
- date (YYYY-MM-DD)
- change summary
- why the change was made
- compatibility impact (patch-safe vs breaking)
- required follow-up tasks for:
  - sonoPleth
  - SpatialSeed
- fixture impact (updated / no change)
- migration notes (if any)

---

## 14) Cross-repo sync protocol (submodule reality)

When a toolchain contract changes in LUSID, agents MUST:
1) implement + test in **LUSID**
2) update this file (`LUSID/internalDocsMD/AGENTS.md`)
3) update `CHANGELOG_TOOLCHAIN.md`
4) update the golden fixture and tests if relevant
5) bump LUSID submodule pointer in **sonoPleth**
6) bump LUSID submodule pointer in **SpatialSeed**
7) update compatibility matrix (Section 16)

Agents MUST NOT land consumer-side hacks without upstreaming the contract change to LUSID.

---

## 15) Documentation governance (the “update toolchain md on data-flow change” rule)

### 15.1 Definition: toolchain-relevant change
A change is toolchain-relevant if it alters any of:
- interchange artifacts (files, names, locations)
- scene schema fields/types/semantics
- ID allocation or WAV mapping rules
- bed/LFE policy or flag semantics
- ADM export channel ordering or chunk requirements
- validation rules or error policy

### 15.2 Mandatory doc update trigger
Agents MUST update:
- `LUSID/internalDocsMD/AGENTS.md` (this file)
- `LUSID/internalDocsMD/CHANGELOG_TOOLCHAIN.md`
- compatibility matrix (Section 16)
- golden fixture spec + asset folder if contract-affecting

---

## 16) Compatibility matrix (must be maintained)

Update whenever contracts change.

| LUSID schema | Min sonoPleth compatible | Min SpatialSeed compatible | Notes |
|---|---|---|---|
| 0.5.2 | (fill: commit/tag) | (fill: commit/tag) | prototype beds+LFE locked |

---

## 17) Security + path hygiene rules

All file IO MUST:
- prevent path traversal (`../`) from metadata-controlled paths
- treat JSON as untrusted input (validate types, ranges)
- never execute code from package contents

---

## 18) Performance budget rules

Agents MUST avoid algorithmic regressions:
- do not add repeated JSON parsing in hot loops
- cache layout computations where possible
- avoid O(N_frames × N_nodes × N_speakers) surprises unless justified

If modifying core render loops, PR MUST include:
- complexity impact note
- microbenchmark or rationale

---

## 19) Experiment lanes (scale experimentation safely)

Experiments MUST land in explicit lanes:
- new node types: allowed, but must be ignored by default consumers
- new export modes: must be behind flags, default off unless adopted
- new package artifacts: optional behind flags; cannot become required without doc + fixture + version rules

Agents MUST NOT “accidentally” turn an experiment into a contract.

---

## 20) Refactor protocol (contract-first)

Before refactoring any pipeline boundary, agents MUST write (in PR description):
- boundary inputs
- boundary outputs
- invariants preserved
- potential breakage risks
- doc impact checklist (below)

---

## 21) PR checklist (agents MUST include in toolchain-impact PRs)

- **Data-flow impact:** none / package layout / schema / export / renderer mapping
- **Docs updated:** AGENTS.md / CHANGELOG_TOOLCHAIN.md / compatibility matrix
- **Flags impacted:** list keys (added/changed defaults)
- **Fixture impact:** updated / no change
- **Backward compatible:** yes/no
- **Validation run:** yes/no (must be yes if impact != none)

---

## 22) Agent instruction: prompt Lucian for tomorrow’s setup tasks (2026-02-11)

If the following folders/files do not exist yet (or are placeholders), agents MUST prompt Lucian to create/source them **tomorrow**:

### 22.1 Required folders/files to create or confirm
- `LUSID/config/toolchain_flags.json` (committed defaults)
- `LUSID/internalDocsMD/CHANGELOG_TOOLCHAIN.md` (contract changelog)
- `LUSID/fixtures/golden_package_v0.5.2/` (fixture folder)

### 22.2 Required fixture assets Lucian must provide/approve
Agents MUST ask Lucian to choose one:
- **Option A:** fixture WAVs are pure silence (fastest; fully deterministic)
- **Option B:** fixture WAVs include tiny test tones (still deterministic; easier audible debugging)

Agents MUST ask Lucian to confirm:
- desired fixture duration (default 0.25–1.0 s)
- acceptable WAV format (default: mono 48k; int16 or float32 acceptable)

### 22.3 Required action after creation
After Lucian creates/sources the above, agents MUST:
- run toolchain validation on the golden fixture
- update compatibility matrix with the commits/tags used
- add initial baseline entry in CHANGELOG_TOOLCHAIN.md

---

## 23) Anti-regression rules (never again)

Agents MUST NOT:
- resurrect `renderInstructions.json` as a pipeline dependency
- resurrect `src_N.wav` naming
- hardcode Atmos bed semantics outside the bed mapping/template layer
- introduce new required package files without updating this contract + fixture + changelog
- change contract behavior without updating documentation + logs
