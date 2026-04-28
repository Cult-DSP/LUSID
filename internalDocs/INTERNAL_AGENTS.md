# LUSID Internal Agent Guide

This document is for agents maintaining the LUSID repository itself.

For external agents that only need to use LUSID in another project, see:

```txt
../AGENTS.md
```

## Repository Role

LUSID is a **spec-only** repository.

It contains:

- schema
- documentation
- examples or templates
- internal design notes
- archival development history

It must not contain runtime code.

## Maintainer-Agent Goal

When editing this repo, preserve the LUSID scene contract as a small, portable, implementation-agnostic specification for spatial audio metadata.

The main responsibility is to keep the following aligned:

```txt
README.md
AGENTS.md
schema/lusid_scene_v1.0.schema.json
internalDocs/DESIGNDOC.md
internalDocs/DEVELOPMENT.md
examples/
```

## Hard Boundary

Do not add or document active runtime behavior in this repo.

Avoid adding:

- parsers
- loaders
- renderers
- playback engines
- CLIs
- project-specific package readers
- speaker layout mappers
- DBAP or VBAP implementations
- ADM conversion pipelines
- MPEG-H or IAMF conversion pipelines
- application code
- build-system logic for runtime tools

If runtime behavior is needed, document it in the consuming project.

## Canonical Source of Truth

The canonical machine-readable source is:

```txt
schema/lusid_scene_v1.0.schema.json
```

The human-facing overview is:

```txt
README.md
```

The public agent-facing guide is:

```txt
AGENTS.md
```

Internal rationale lives in:

```txt
internalDocs/DESIGNDOC.md
```

Historical notes live in:

```txt
internalDocs/DEVELOPMENT.md
```

## Version Discipline

Current documentation release:

```txt
LUSID Scene v1.0
```

Current schema scene version:

```json
"version": "1.0"
```

Do not change the schema `version` value unless the schema is intentionally versioned.

If the schema changes in a way that affects compatibility:

1. update the schema
2. update README
3. update AGENTS
4. update internalDocs/DESIGNDOC if the design intent changed
5. update examples
6. note the change in DEVELOPMENT

## Schema Editing Rules

When editing the schema:

- preserve `additionalProperties: false` for strict playback-critical node types unless deliberately changed
- preserve metadata flexibility for node types designed to allow arbitrary fields
- keep descriptions accurate and implementation-agnostic
- avoid renderer-specific language
- avoid project-specific language
- avoid assuming a particular consuming runtime
- keep node semantics separate from runtime routing

If a field is optional, document whether it is optional because of compatibility, metadata use, or consuming-project responsibility.

## Documentation Editing Rules

When editing public docs:

- keep README human-facing
- keep AGENTS agent-facing
- keep internalDocs development-facing
- do not duplicate long historical notes in public docs
- do not expose old implementation tasks as current instructions
- do not describe deprecated runtime code as active
- keep examples and schema synchronized

## Internal Documentation Roles

### `DESIGNDOC.md`

Use this for:

- design intent
- format rationale
- influences
- why the schema is structured this way
- constraints that should inform future schema changes

Do not use this as a public integration guide.

### `DEVELOPMENT.md`

Use this for:

- archived history
- old implementation context
- migration notes
- deprecated files or removed runtime paths

Do not use this as current implementation guidance.

### `INTERNAL_AGENTS.md`

Use this for:

- maintainer-agent rules
- repo safety constraints
- schema/doc synchronization rules
- public vs internal documentation boundaries

## Public vs Internal Agent Docs

Root `AGENTS.md` is for external use:

```txt
“How do I use LUSID in my project?”
```

`internalDocs/INTERNAL_AGENTS.md` is for maintenance:

```txt
“How do I safely edit the LUSID repo?”
```

Do not merge these roles.

## Node Model Invariants

Preserve these core concepts unless intentionally revising the format:

- scene data is represented as ordered frames
- each frame has a timestamp and nodes
- nodes use hierarchical IDs in `X.Y` form
- `X` identifies a logical group
- `Y = 1` identifies the primary node
- `Y >= 2` identifies child or metadata nodes
- `audio_object` nodes carry spatial position
- `direct_speaker` nodes represent fixed bed channels
- `LFE` nodes represent low-frequency content without position
- metadata layers may attach to primary groups

## Coordinate Invariants

Preserve the Cartesian coordinate convention:

```txt
x: left negative, right positive
y: back negative, front positive
z: down negative, up positive
```

Spatial nodes use:

```json
"cart": [x, y, z]
```

Do not redefine these axes without a schema version change.

## Time Invariants

Preserve explicit time-unit declaration.

Allowed values:

```txt
seconds / s
samples / samp
milliseconds / ms
```

If `timeUnit` is `samples`, `sampleRate` should be present.

Do not imply a project-specific clock, block size, buffer size, or renderer tick rate.

## Runtime Language to Avoid

Avoid phrases like:

- “LUSID renders”
- “LUSID routes”
- “LUSID plays”
- “LUSID maps to speakers”
- “LUSID loads audio”
- “LUSID interpolates”
- “LUSID decodes ADM”

Prefer:

- “A consuming project may render”
- “A runtime may map”
- “A parser may consume”
- “A tool may generate”
- “A renderer may interpret”
- “LUSID represents”

## Safe Edit Checklist

Before completing an edit:

- schema still validates as JSON Schema
- examples validate against schema
- README still says repo is spec-only
- AGENTS still describes external use only
- INTERNAL_AGENTS still describes maintenance only
- no runtime implementation has been added
- no renderer-specific behavior has been defined as part of LUSID
- version references are consistent
- schema filename references are consistent
