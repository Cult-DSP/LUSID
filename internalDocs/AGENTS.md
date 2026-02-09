## LUSID Agent Specification — Scene v0.5 → sonoPleth Renderer

**Updated:** 2026-02-09  
**Author:** LUSID / sonoPleth Integration Team  
**Purpose:** This document provides agent-level instructions for implementing a LUSID Scene v0.5 transcoder inside the sonoPleth repository. The agent transforms a LUSID JSON scene (time-based node graph) into a `renderInstructions.json` compatible with sonoPleth’s spatial audio renderer.

---

## 🧠 Summary

LUSID Scene v0.5 represents spatial audio and metadata as a timeline of timestamped frames. Each frame contains "nodes" with hierarchical IDs (`X.Y`) and types (`audio_object`, `LFE`, `spectral_features`, `agent_state`, etc.).

This agent will:

- Parse and validate a LUSID scene file
- Convert audio object trajectories into sonoPleth-compatible source keyframes
- Handle LFE routing
- Export optional spectral and agent state data
- Output `renderInstructions.json` for downstream rendering
