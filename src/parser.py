"""
LUSID Scene v0.5 — Parser

Loads a LUSID JSON file into a LusidScene data model.
Validates structure, sorts frames by time, warns on problems,
but always tries to return a usable scene (graceful fallback).
"""

from __future__ import annotations
import json
import math
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .scene import (
    AudioObjectNode,
    AgentStateNode,
    Frame,
    LFENode,
    LusidScene,
    Node,
    SpectralFeaturesNode,
    normalize_time_unit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NODE_ID_PATTERN_DESC = "'X.Y' where X and Y are integers"


def _warn(msg: str) -> None:
    """Issue a non-fatal warning."""
    warnings.warn(f"[LUSID parser] {msg}", stacklevel=3)


def _is_valid_node_id(raw: str) -> bool:
    """Check if a node ID matches the X.Y integer pattern."""
    parts = raw.split(".")
    if len(parts) != 2:
        return False
    try:
        int(parts[0])
        int(parts[1])
        return True
    except ValueError:
        return False


def _is_finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(v)


# ---------------------------------------------------------------------------
# Node parsing
# ---------------------------------------------------------------------------

def _parse_node(raw: Dict[str, Any]) -> Optional[Node]:
    """
    Parse a single node dict into a typed Node object.
    Returns None (with warning) if the node is malformed.
    """
    node_id = raw.get("id")
    node_type = raw.get("type")

    # -- required fields --
    if node_id is None:
        _warn(f"Node missing 'id', skipping: {raw}")
        return None
    node_id = str(node_id)

    if not _is_valid_node_id(node_id):
        _warn(f"Node id '{node_id}' does not match {_NODE_ID_PATTERN_DESC}, skipping")
        return None

    if node_type is None:
        _warn(f"Node '{node_id}' missing 'type', skipping")
        return None

    # -- dispatch by type --
    if node_type == "audio_object":
        return _parse_audio_object(node_id, raw)
    elif node_type == "LFE":
        return LFENode(id=node_id)
    elif node_type == "spectral_features":
        return _parse_spectral_features(node_id, raw)
    elif node_type == "agent_state":
        return _parse_agent_state(node_id, raw)
    else:
        _warn(f"Node '{node_id}' has unknown type '{node_type}', skipping")
        return None


def _parse_audio_object(node_id: str, raw: Dict[str, Any]) -> Optional[AudioObjectNode]:
    cart = raw.get("cart")
    if cart is None:
        _warn(f"audio_object '{node_id}' missing 'cart', skipping")
        return None
    if not isinstance(cart, list) or len(cart) < 3:
        _warn(f"audio_object '{node_id}' 'cart' must be [x, y, z], skipping")
        return None

    x, y, z = cart[0], cart[1], cart[2]
    if not all(_is_finite(v) for v in (x, y, z)):
        _warn(f"audio_object '{node_id}' has NaN/Inf in cart, skipping")
        return None

    gain = raw.get("gain", 1.0)
    if not _is_finite(gain):
        _warn(f"audio_object '{node_id}' has invalid gain, defaulting to 1.0")
        gain = 1.0

    return AudioObjectNode(id=node_id, cart=[float(x), float(y), float(z)], gain=float(gain))


def _parse_spectral_features(node_id: str, raw: Dict[str, Any]) -> SpectralFeaturesNode:
    # Collect all fields except id and type as data
    data = {k: v for k, v in raw.items() if k not in ("id", "type")}
    return SpectralFeaturesNode(id=node_id, data=data)


def _parse_agent_state(node_id: str, raw: Dict[str, Any]) -> AgentStateNode:
    data = {k: v for k, v in raw.items() if k not in ("id", "type")}
    return AgentStateNode(id=node_id, data=data)


# ---------------------------------------------------------------------------
# Frame parsing
# ---------------------------------------------------------------------------

def _parse_frame(raw: Dict[str, Any], index: int) -> Optional[Frame]:
    """Parse a single frame dict. Returns None if frame is fatally malformed."""
    time_val = raw.get("time")
    if time_val is None:
        _warn(f"Frame at index {index} missing 'time', skipping")
        return None
    if not _is_finite(time_val):
        _warn(f"Frame at index {index} has invalid time={time_val}, skipping")
        return None

    raw_nodes = raw.get("nodes")
    if raw_nodes is None:
        _warn(f"Frame at time={time_val} missing 'nodes', treating as empty")
        raw_nodes = []
    if not isinstance(raw_nodes, list):
        _warn(f"Frame at time={time_val} 'nodes' is not a list, treating as empty")
        raw_nodes = []

    # Check for duplicate node IDs within frame
    seen_ids: set[str] = set()
    nodes: List[Node] = []
    for rn in raw_nodes:
        if not isinstance(rn, dict):
            _warn(f"Frame at time={time_val}: non-dict node entry, skipping")
            continue
        node = _parse_node(rn)
        if node is None:
            continue
        if node.id in seen_ids:
            _warn(f"Frame at time={time_val}: duplicate node id '{node.id}', keeping last")
            nodes = [n for n in nodes if n.id != node.id]
        seen_ids.add(node.id)
        nodes.append(node)

    return Frame(time=float(time_val), nodes=nodes)


# ---------------------------------------------------------------------------
# Scene-level parsing
# ---------------------------------------------------------------------------

def parse_file(path: Union[str, Path]) -> LusidScene:
    """
    Load and parse a LUSID Scene v0.5 JSON file.

    Parameters
    ----------
    path : str or Path
        Path to the JSON file.

    Returns
    -------
    LusidScene
        Parsed scene. May have fewer frames/nodes than the file
        if validation warnings were issued.

    Raises
    ------
    FileNotFoundError
        If the file doesn't exist.
    json.JSONDecodeError
        If the file isn't valid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"LUSID scene file not found: {path}")

    with open(path, "r") as f:
        raw = json.load(f)

    return parse_dict(raw)


def parse_dict(raw: Dict[str, Any]) -> LusidScene:
    """
    Parse a LUSID scene from an already-loaded dict.

    Parameters
    ----------
    raw : dict
        Top-level JSON object.

    Returns
    -------
    LusidScene
    """
    # -- version --
    version = raw.get("version")
    if version is None:
        _warn("Missing 'version' field, assuming '0.5'")
        version = "0.5"
    version = str(version)
    if version != "0.5":
        _warn(f"Expected version '0.5', got '{version}'. Attempting to parse anyway.")

    # -- timeUnit --
    raw_time_unit = raw.get("timeUnit", "seconds")
    try:
        time_unit = normalize_time_unit(str(raw_time_unit))
    except ValueError as e:
        _warn(str(e) + " — defaulting to 'seconds'")
        time_unit = "seconds"

    # -- sampleRate --
    sample_rate = raw.get("sampleRate")
    if sample_rate is not None:
        if not isinstance(sample_rate, (int, float)) or sample_rate <= 0:
            _warn(f"Invalid sampleRate={sample_rate}, ignoring")
            sample_rate = None
        else:
            sample_rate = int(sample_rate)

    if time_unit == "samples" and sample_rate is None:
        _warn("timeUnit is 'samples' but no valid sampleRate provided. "
              "Time conversion to seconds will fail.")

    # -- metadata --
    metadata = raw.get("metadata", {})
    if not isinstance(metadata, dict):
        _warn("'metadata' is not a dict, ignoring")
        metadata = {}

    # -- frames --
    raw_frames = raw.get("frames")
    if raw_frames is None:
        _warn("Missing 'frames' array — scene will be empty")
        raw_frames = []
    if not isinstance(raw_frames, list):
        _warn("'frames' is not a list — scene will be empty")
        raw_frames = []

    frames: List[Frame] = []
    for i, rf in enumerate(raw_frames):
        if not isinstance(rf, dict):
            _warn(f"Frame at index {i} is not a dict, skipping")
            continue
        frame = _parse_frame(rf, i)
        if frame is not None:
            frames.append(frame)

    # Sort frames by time (ascending)
    frames.sort(key=lambda f: f.time)

    return LusidScene(
        version=version,
        frames=frames,
        time_unit=time_unit,
        sample_rate=sample_rate,
        metadata=metadata,
    )
