# LUSID Scene v1.0

**Lightweight Universal Spatial Interaction Data**

LUSID is a JSON scene specification for spatial audio metadata. It represents a scene as a time-sequenced set of frames, where each frame contains spatial nodes, fixed speaker nodes, low-frequency nodes, and optional metadata layers.

This repository is **spec-only**. It contains the schema, documentation, and templates needed to generate or validate LUSID scenes. Runtime tools live outside this repo.

## What LUSID Is

LUSID defines a portable scene contract for spatial audio systems.

A LUSID scene can describe:

- moving audio objects
- fixed direct-speaker bed channels
- LFE content
- frame-based spatial position data
- analysis metadata attached to scene nodes
- agent or procedural state attached to scene nodes

The canonical reference is:

```txt
schema/lusid_scene_v1.0.schema.json
```

## What This Repo Contains

```txt
LUSID/
├── README.md
├── AGENTS.md
├── schema/
│   └── lusid_scene_v1.0.schema.json
└── internalDocs/
    ├── INTERNAL_AGENTS.md
    ├── DESIGNDOC.md
    └── DEVELOPMENT.md
```

### Public Files

- `README.md`  
  Human-facing overview of the LUSID scene format.

- `AGENTS.md`  
  Agent-facing guide for using LUSID in another project.

- `schema/lusid_scene_v1.0.schema.json`  
  Canonical JSON Schema for LUSID Scene v1.0.

### Internal Development Files

- `internalDocs/INTERNAL_AGENTS.md`  
  Maintainer-agent instructions for editing this repo safely.

- `internalDocs/DESIGNDOC.md`  
  Internal design rationale and format influences.

- `internalDocs/DEVELOPMENT.md`  
  Archival development history.

The `internalDocs/` folder is development-facing. It is not required for consuming or generating LUSID scenes.

## What This Repo Does Not Contain

This repo does **not** provide:

- audio playback
- speaker layout mapping
- spatial rendering
- DBAP, VBAP, or other panning algorithms
- ADM parsing
- MPEG-H or IAMF parsing
- file packaging tools
- runtime interpolation behavior
- loaders, parsers, CLIs, or application code

Projects that use LUSID are responsible for their own runtime behavior.

## Basic Scene Model

A LUSID scene is a JSON object with:

- a format version
- optional sample rate
- optional duration
- optional metadata
- a list of time-ordered frames

Each frame contains a timestamp and a list of active nodes.

Minimal structure:

```json
{
  "version": "1.0",
  "sampleRate": 48000,
  "timeUnit": "seconds",
  "frames": [
    {
      "time": 0.0,
      "nodes": [
        {
          "id": "11.1",
          "type": "audio_object",
          "cart": [0.0, 1.0, 0.0]
        }
      ]
    }
  ]
}
```

## Node Types

| Type | Description |
| ---- | ----------- |
| `audio_object` | Spatial audio source with Cartesian position |
| `direct_speaker` | Fixed bed channel with optional speaker metadata |
| `LFE` | Low-frequency effects node with no position |
| `spectral_features` | Analysis metadata attached to a parent group |
| `agent_state` | Agent or procedural metadata attached to a parent group |

## Node ID Convention

LUSID uses hierarchical node IDs in the form:

```txt
X.Y
```

Where:

- `X` is the group number
- `Y` is the hierarchy level
- `Y = 1` identifies the primary node in a group
- `Y >= 2` identifies metadata or child nodes attached to that group

Examples:

```txt
11.1    primary audio object in group 11
11.2    metadata attached to group 11
11.3    additional metadata attached to group 11
```

Recommended conventions:

- groups `1-10`: direct-speaker bed channels
- group `4`: conventional LFE group
- groups `11+`: audio objects

These conventions are intended to keep generated scenes predictable and readable.

## Coordinate System

Spatial nodes use Cartesian direction vectors:

```json
"cart": [x, y, z]
```

Coordinate meaning:

| Axis | Meaning |
| ---- | ------- |
| `x` | left negative, right positive |
| `y` | back negative, front positive |
| `z` | down negative, up positive |

Vectors are expected to be normalized direction vectors unless a consuming project explicitly defines another interpretation.

## Time Units

The top-level `timeUnit` field defines the unit used for all frame timestamps.

Allowed values:

| Value | Alias | Meaning |
| ----- | ----- | ------- |
| `seconds` | `s` | timestamps are seconds |
| `samples` | `samp` | timestamps are sample indices |
| `milliseconds` | `ms` | timestamps are milliseconds |

If `timeUnit` is `samples`, `sampleRate` should be provided.

## Using LUSID in Another Project

To use LUSID in another project:

1. Reference or vendor the schema.
2. Generate scene JSON that follows the schema.
3. Validate generated scenes against the schema.
4. Implement runtime interpretation in the consuming project.

For coding agents or automated integrations, see:

```txt
AGENTS.md
```

## Validation

Generated scenes should validate against:

```txt
schema/lusid_scene_v1.0.schema.json
```

Validation should be treated as the source of truth for compatibility.

## Design Principles

LUSID is designed to be:

- schema-first
- human-readable
- deterministic
- implementation-agnostic
- useful as a handoff format between tools
- strict about playback-critical data
- flexible for non-playback metadata

## Development Notes

Internal design rationale and historical development notes live in:

```txt
internalDocs/
```

These files are useful for maintainers but are not required for external projects that only need to generate or consume LUSID scenes.
