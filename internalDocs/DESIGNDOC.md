# LUSID Scene v1.0 — Design Decisions and Influences

**Internal design rationale for the LUSID scene specification**  
**Last Updated:** April 27, 2026

## Scope

This document captures the design intent and historical influences behind the LUSID scene format.

LUSID is a **spec-only** scene contract. This document does not define runtime tools, playback behavior, loaders, renderers, or pipelines.

## Design Goal

LUSID exists to provide a small, portable, human-readable scene representation for spatial audio metadata.

The format is intended to sit between tools. A converter, authoring system, analysis process, or procedural generator can output a LUSID scene. A renderer, playback system, visualization tool, or research environment can consume it. LUSID defines the handoff structure, not the behavior of either side.

## Core Design Principles

### Schema First

The JSON Schema is the canonical machine-readable contract.

Documentation should explain the schema, not replace it. Examples should validate against it.

### Spec Only

LUSID does not define runtime behavior.

It represents scene data. It does not play audio, map speakers, choose panning algorithms, parse ADM, decode delivery formats, or define interpolation behavior.

### Human Readable

A LUSID scene should be readable and inspectable as JSON.

Node IDs, frame timestamps, coordinate vectors, and metadata layers are designed to be understandable without specialized tooling.

### Deterministic

The format stores explicit frame states. A frame contains the active node state at a given time.

Any interpolation, smoothing, buffering, or renderer-specific behavior is handled by the consuming project.

### Implementation Agnostic

LUSID should be usable from C++, Python, JavaScript, Rust, Max/MSP-adjacent tooling, DAW utilities, research scripts, and custom spatial audio engines.

The schema should avoid assumptions about one runtime, one renderer, one speaker layout, or one authoring workflow.

### Metadata Extensibility

Playback-critical node types are strict. Metadata node types may remain flexible.

This allows the format to represent spatial scene data while still carrying analysis, procedural, or agent-oriented context.

## Core Design Decisions

## Node Graph with Grouped IDs

LUSID uses node IDs in the form:

```txt
X.Y
```

Where:

- `X` is a logical group number
- `Y` is a hierarchy level
- `Y = 1` is the primary node
- `Y >= 2` is a child or metadata node attached to the same group

### Why

This creates a simple, human-readable way to bind metadata to a primary spatial object without requiring explicit parent arrays or complex graph references.

For example:

```txt
11.1    primary audio object
11.2    spectral features for group 11
11.3    agent state for group 11
```

### Effect

A consuming project can associate metadata nodes with their primary node by group number.

The ID convention also keeps generated scenes predictable and easy to inspect.

## Frame-Based Timeline

LUSID represents scenes as ordered frames.

Each frame contains:

- a timestamp
- a list of active nodes

### Why

A frame-based timeline is simple, deterministic, and easy to validate.

It avoids embedding implicit animation curves or renderer-specific interpolation assumptions into the spec.

### Effect

The scene stores explicit state at each time point.

A consuming project may interpolate between frames, but interpolation is not defined by LUSID.

## Explicit Time Units

LUSID uses a top-level `timeUnit` field.

Allowed values:

```txt
seconds / s
samples / samp
milliseconds / ms
```

### Why

Spatial audio pipelines may use seconds, sample indices, or milliseconds depending on their source format and runtime context.

Explicit time units avoid ambiguity.

### Effect

Frame timestamps are interpreted according to the top-level `timeUnit` field.

If `timeUnit` is `samples`, a `sampleRate` should be included.

## Cartesian Coordinate System

Spatial nodes use:

```json
"cart": [x, y, z]
```

With the convention:

```txt
x: left negative, right positive
y: back negative, front positive
z: down negative, up positive
```

### Why

Cartesian direction vectors are simple to generate, inspect, and map into multiple renderer types.

They also align with the needs of layout-agnostic spatial audio systems that may later transform scene coordinates into a renderer-specific representation.

### Effect

LUSID stores spatial position as data. It does not define how that position is rendered.

A consuming runtime may map the vector to DBAP, VBAP, ambisonics, direct speaker assignment, visualization, or another spatial model.

## Direct-Speaker Nodes

The `direct_speaker` node type represents fixed bed channels.

A direct-speaker node may include:

- `cart`
- `speakerLabel`
- `channelID`

### Why

Many object-based formats include a distinction between moving objects and fixed bed channels.

LUSID needs to represent both while keeping the scene structure uniform.

### Effect

A direct-speaker node is a fixed spatial scene node. It is not a device routing instruction.

Fields such as `speakerLabel` and `channelID` are informational metadata unless a consuming project chooses to interpret them.

## LFE Nodes

The `LFE` node type represents low-frequency effects content.

LFE nodes do not require Cartesian position.

### Why

Low-frequency content is usually handled as a special semantic class rather than as a normal spatial object.

### Effect

LUSID can preserve the existence of LFE content without forcing a spatial position that may be misleading.

Runtime routing of LFE content belongs to the consuming project.

## Metadata Layers

LUSID supports child metadata nodes such as:

- `spectral_features`
- `agent_state`

These use the same `X.Y` group convention as primary nodes.

### Why

Spatial scenes often need auxiliary information: analysis features, procedural state, agent state, generative controls, or other non-playback metadata.

Attaching this information as child nodes keeps playback-critical object data clean while preserving extensibility.

### Effect

A LUSID scene can carry richer context without requiring every metadata field to become part of the core spatial object definition.

## Influences

### glTF

glTF influenced the general idea of a portable, structured scene description that can be consumed by multiple downstream tools.

The LUSID node model is much simpler than glTF. LUSID does not attempt to reproduce glTF's full scene graph, asset model, animation system, or binary packaging. The relevant influence is the broader idea of a compact scene contract that separates representation from runtime rendering.

### ADM and Dolby Atmos Workflows

ADM and Atmos-centered workflows influenced the distinction between object-like spatial metadata, direct speaker or bed-like elements, and LFE semantics.

LUSID does not attempt to be ADM. It does not encode the full ADM object model or production metadata structure. Instead, it preserves the spatial scene information needed for downstream open tools.

### Existing sonoPleth / Spatial Root Scene Data

Earlier project data structures influenced LUSID's explicit time units, Cartesian vectors, and practical focus on layout-agnostic scene handoff.

Those histories informed the format, but LUSID is now maintained as a standalone spec-only repo.

## Design Constraints

LUSID should remain:

- small
- JSON-based
- schema-first
- inspectable
- implementation-agnostic
- usable without a runtime dependency
- strict where playback-critical
- flexible where metadata-oriented

## Non-Goals

LUSID does not aim to be:

- a renderer
- an audio engine
- an ADM replacement
- a DAW session format
- a complete multimedia asset package
- a speaker layout format
- a network protocol
- a real-time control protocol
- a complete animation system

Future tools may use LUSID alongside any of these systems, but those behaviors should not be folded into the core scene specification unless the scope of the format is intentionally revised.

## Compatibility Expectations

A valid LUSID v1.0 scene should:

- use `"version": "1.0"`
- validate against the v1.0 schema
- contain ordered frames
- use `X.Y` node IDs
- use `cart` for spatial nodes that require position
- keep LFE nodes position-free
- keep runtime assumptions outside the scene file

## Future Expansion Areas

Possible future extensions may include:

- additional metadata node types
- stronger package conventions
- optional spherical coordinate fields
- versioned profiles for different consuming environments
- richer validation around frame ordering or duration
- formal example suites
- compatibility notes for specific consuming projects

These should be added carefully. Any expansion should preserve the core role of LUSID as a portable scene contract rather than a runtime system.
