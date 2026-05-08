# LUSID Agent Guide

This document is for coding agents or automated tools that have been given this repository and need to use LUSID in another project.

LUSID is a **schema-only spatial audio scene contract**. It is not a runtime, renderer, parser, package manager, or audio engine.

## Primary Goal

Use this repo to generate, validate, or consume LUSID-compatible scene metadata.

The canonical file is:

```txt
schema/lusid_scene_v1.0.schema.json
```

Generated scenes must validate against this schema.

## What LUSID Provides

LUSID provides:

- a JSON structure for spatial audio scenes
- a frame-based timeline model
- spatial node types
- direct-speaker node types
- LFE node representation
- metadata child-node conventions
- Cartesian coordinate conventions
- timestamp unit conventions

## What LUSID Does Not Provide

Do not assume this repo provides:

- audio playback
- speaker mapping
- renderer behavior
- DBAP, VBAP, ambisonic, or other spatialization algorithms
- ADM parsing
- MPEG-H or IAMF parsing
- file loading behavior
- package loading behavior
- interpolation rules
- audio engine code
- CLI tools
- runtime APIs

Any of these behaviors belong in the consuming project, not in the LUSID repo.

## When Using LUSID in Another Project

A consuming project may:

- reference the LUSID schema by path or URL
- vendor the schema into its own repo
- use LUSID as a Git submodule
- generate `scene.lusid.json` files
- validate generated scenes against the schema
- map LUSID nodes into its own runtime model

A consuming project is responsible for:

- file IO
- audio file management
- renderer mapping
- loudspeaker layout interpretation
- interpolation
- real-time playback
- offline rendering
- format conversion
- error handling

## Canonical Scene Rules

A valid LUSID scene must follow the schema.

Basic structure:

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

Do not change the `version` value unless the schema is versioned accordingly.

## Frame Rules

Scenes are represented as ordered frames.

Each frame must contain:

```json
{
  "time": 0.0,
  "nodes": []
}
```

Rules:

- `time` uses the top-level `timeUnit`
- `nodes` contains all active nodes for that frame
- frames should be ordered by time
- each frame is a scene snapshot
- interpolation is not defined by LUSID

If a consuming project interpolates between frames, that is project-specific runtime behavior.

## Node ID Rules

Node IDs use the format:

```txt
X.Y
```

Where:

- `X` is the group number
- `Y` is the hierarchy level
- `Y = 1` is the primary node for a group
- `Y >= 2` is a child or metadata node attached to the group

Examples:

```txt
11.1    primary audio object
11.2    spectral metadata for group 11
11.3    agent metadata for group 11
```

Recommended group conventions:

- `1-10`: direct-speaker bed channels
- `4`: conventional LFE group
- `11+`: audio objects

## Node Type Rules

### `audio_object`

Use for spatial audio sources.

Required fields:

```json
{
  "id": "11.1",
  "type": "audio_object",
  "cart": [0.0, 1.0, 0.0]
}
```

Optional fields:

```json
"gain": 1.0
```

Do not add unsupported fields to `audio_object` unless the schema allows them.

### `direct_speaker`

Use for fixed bed channels.

Required fields:

```json
{
  "id": "1.1",
  "type": "direct_speaker",
  "cart": [-1.0, 1.0, 0.0]
}
```

Optional informational fields:

```json
"speakerLabel": "RC_L",
"channelID": "AC_00011001"
```

`direct_speaker` describes a fixed scene node. It does not define device routing or runtime speaker mapping.

### `LFE`

Use for low-frequency effects.

Required fields:

```json
{
  "id": "4.1",
  "type": "LFE"
}
```

Do not add `cart` to `LFE` nodes unless the schema changes.

### `spectral_features`

Use for analysis metadata attached to a parent group.

Example:

```json
{
  "id": "11.2",
  "type": "spectral_features",
  "centroid": 5000.0,
  "flux": 0.15,
  "bandwidth": 1200.0
}
```

Additional properties are allowed for this node type.

### `agent_state`

Use for agent, procedural, or generative state attached to a parent group.

Example:

```json
{
  "id": "11.3",
  "type": "agent_state",
  "mood": "calm",
  "intensity": 0.25
}
```

Additional properties are allowed for this node type.

## Coordinate Rules

Spatial nodes use:

```json
"cart": [x, y, z]
```

Axis convention:

- `x`: left negative, right positive
- `y`: back negative, front positive
- `z`: down negative, up positive

Use normalized direction vectors unless the consuming project explicitly documents another interpretation.

## Time Unit Rules

Top-level `timeUnit` may be:

```json
"seconds"
"s"
"samples"
"samp"
"milliseconds"
"ms"
```

Preferred value:

```json
"seconds"
```

If using sample timestamps, include:

```json
"sampleRate": 48000
```

## Generation Checklist

Before outputting a LUSID scene:

- confirm top-level `version` is `"1.0"`
- confirm `frames` exists
- confirm every frame has `time` and `nodes`
- confirm frame times are ordered
- confirm every node has `id` and `type`
- confirm node IDs match `X.Y`
- confirm `audio_object` nodes have `cart`
- confirm `direct_speaker` nodes have `cart`
- confirm `LFE` nodes do not require position
- confirm child metadata nodes use `X.2+`
- validate against `schema/lusid_scene_v1.0.schema.json`

## Integration Pattern

For a consuming project, the normal pattern is:

```txt
project/
├── external/
│   └── LUSID/
│       └── schema/
│           └── lusid_scene_v1.0.schema.json
├── scenes/
│   └── scene.lusid.json
└── src/
    └── project-specific runtime code
```

The consuming project should treat LUSID as an input or output contract.

Do not put consuming-project runtime assumptions into the LUSID schema.

## Development Examples

The following CULT DSP projects demonstrate how LUSID can be used in practice. These examples are informative, not normative. They show producer and consumer patterns, but they do not expand the LUSID specification.

### CULT Transcoder: Producer Pattern

[CULT Transcoder](https://github.com/Cult-DSP/cult_transcoder/tree/seed) is an example of a LUSID-producing tool. It converts external spatial audio metadata, especially ADM XML/WAV, into LUSID Scene JSON.

In this pattern, LUSID acts as the normalized scene representation produced after format-specific parsing.

A similar producer in another project should:

- parse its own source format
- map source metadata into LUSID nodes and frames
- write a valid LUSID scene JSON file
- validate the result against the LUSID schema

Format-specific behavior, conversion policy, reports, package creation, and audio processing remain the producer project’s responsibility.

### Spatial Root: Consumer Pattern

[Spatial Root](https://github.com/Cult-DSP/spatialroot) is an example of a LUSID-consuming runtime. It uses LUSID scene JSON as scene metadata for playback and rendering.

In this pattern, LUSID acts as the scene contract passed into a runtime.

A similar consumer in another project should:

- read a valid LUSID scene
- map LUSID nodes into its internal scene model
- apply its own layout, rendering, interpolation, and playback behavior
- keep runtime assumptions outside the LUSID schema

Spatial Root demonstrates one way to consume LUSID, but it does not define mandatory LUSID playback semantics.

### What These Examples Do Not Define

Spatial Root and CULT Transcoder are reference integrations, not normative parts of the LUSID specification.

They do not define:

- required renderer behavior
- required speaker layout behavior
- required ADM conversion policy
- required package structure
- required audio stem naming
- required interpolation behavior
- required CLI behavior
- required report formats

If a behavior is not represented in the LUSID schema, treat it as project-specific.

## If You Need Runtime Behavior

If you need to describe how a renderer, parser, engine, or tool consumes LUSID, write that documentation in the consuming project.

Do not add runtime behavior to this repository.
