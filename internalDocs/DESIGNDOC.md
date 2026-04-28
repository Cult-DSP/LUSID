#+#+#+#+

# LUSID Scene v0.5.2 — Design Decisions and Influences (Spec-Only)

**Internal design rationale for the LUSID scene specification**  
**Last Updated:** April 27, 2026

---

## Scope

This document captures **design intent** and **historical influences** behind the LUSID scene format. It does not describe runtime tools or pipelines.

---

## Core Design Decisions

### Node Graph with Grouped IDs (`X.Y`)

- **Why:** A simple, human-readable way to bind metadata to a primary audio object without explicit parent arrays.
- **Effect:** `X` denotes a logical group; `Y=1` is the primary node; `Y>=2` are child metadata nodes.

### Frame-Based Timeline (Scene Snapshots)

- **Why:** Deterministic playback and simple synchronization across all nodes.
- **Effect:** The scene is a sequence of frames; each frame is a full snapshot of active nodes at time `t`.
- **Implication:** Any interpolation is a producer concern; the spec stores explicit state at each time point.

### Explicit Time Units

- **Why:** Avoid ambiguity across pipelines and preserve timing precision.
- **Decision:** `timeUnit` supports `seconds`, `samples`, and `milliseconds` with optional `sampleRate`.

### Coordinate System

- **Why:** Keep compatibility with existing spatial audio conventions.
- **Decision:** `cart: [x, y, z]` direction vectors are supported; spherical values may appear as secondary fields.

### Extensible Metadata Layers

- **Why:** Enable analysis or agent context to live alongside spatial data.
- **Decision:** `spectral_features` and `agent_state` are child node types; unknown types are allowed by design.

---

## Influences

### glTF 2.0

- Node-based scene graphs influenced the `X.Y` grouping concept.
- Animation sampling inspired the choice to store explicit snapshots rather than implicit curves.

### ADM (Dolby Atmos)

- Object-based spatial metadata influenced the `audio_object` node definition.
- The LFE role shaped the `LFE` node type as a special-case semantic.

### sonoPleth JSON

- Explicit `timeUnit` and sample-rate context informed the time model.
- Use of Cartesian direction vectors informed the `cart` field.

---

## Design Constraints (Spec-Only)

- No runtime behavior is defined here.
- Schema and examples are the only source of truth.
- Any pipeline behavior belongs in external tools and their docs.
