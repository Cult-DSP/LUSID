# LUSID Scene v0.5.2 — Specification

LUSID defines a time-sequenced node graph for spatial audio scenes. This repository is **spec-only**: schema, documentation, and templates. Runtime tools live outside this repo.

## Overview

LUSID Scene v0.5 represents spatial audio scenes as a timeline of **frames**, each containing **nodes** with hierarchical IDs (`X.Y`) and typed data. The canonical reference is the JSON schema in [schema/lusid_scene_v0.5.schema.json](schema/lusid_scene_v0.5.schema.json).

## Scope

- This repo provides the **specification** and templates only.
- Do not add or document runtime behavior here.
- Runtime tools should reference this spec, not be implemented within it.

## Node Types

| Type                | ID Convention | Description                                                   |
| ------------------- | ------------- | ------------------------------------------------------------- |
| `direct_speaker`    | `X.1`         | Fixed bed channel with `cart`, `speakerLabel`, `channelID`    |
| `audio_object`      | `X.1`         | Spatial audio source with time-varying `cart` [x,y,z]         |
| `LFE`               | `X.1`         | Low-frequency effects — routed to subwoofers, not spatialized |
| `spectral_features` | `X.2+`        | Spectral analysis data (centroid, flux, bandwidth, etc.)      |
| `agent_state`       | `X.2+`        | AI/agent metadata (mood, intensity, etc.)                     |

### Node ID Convention (`X.Y`)

- **X** = group number (logical grouping of related nodes)
- **Y** = hierarchy level (1 = parent/primary, 2+ = child/metadata)

Groups 1–10: DirectSpeaker bed channels. Group 4: LFE (conventional). Groups 11+: Audio objects.

## Templates

Use [schema/lusid_scene_v0.5.schema.json](schema/lusid_scene_v0.5.schema.json) as the canonical template for generating scenes.

## Coordinate System

- `cart: [x, y, z]` — Cartesian direction vector
  - **x**: Left (−) / Right (+)
  - **y**: Back (−) / Front (+)
  - **z**: Down (−) / Up (+)
- Vectors are expected to be unit length

## Time Units

Specify via the top-level `timeUnit` field:

| Value            | Aliases  | Description                            |
| ---------------- | -------- | -------------------------------------- |
| `"seconds"`      | `"s"`    | Default. Timestamps in seconds         |
| `"samples"`      | `"samp"` | Sample indices (requires `sampleRate`) |
| `"milliseconds"` | `"ms"`   | Timestamps in milliseconds             |

## File Structure

```
LUSID/
├── schema/
│   └── lusid_scene_v0.5.schema.json     # JSON Schema
└── internalDocs/
    ├── LUSID_AGENTS.md                   # Agent-level specification
    ├── DEVELOPMENT.md                    # Archival history
    └── conceptNotes.md                   # Original design notes
```

## See Also

- [internalDocs/LUSID_AGENTS.md](internalDocs/LUSID_AGENTS.md) — Spec-only agent guidance
- [internalDocs/DEVELOPMENT.md](internalDocs/DEVELOPMENT.md) — Archival history
