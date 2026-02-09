"""
LUSID Scene v0.5 — Transcoder

Converts a LusidScene into sonoPleth renderInstructions.json format.

Output structure (sonoPleth):
{
  "sampleRate": 48000,
  "timeUnit": "seconds",
  "sources": {
    "src_<group>": [ {"time": t, "cart": [x,y,z]}, ... ],
    "LFE":         [ {"time": 0.0} ]
  }
}

Non-audio nodes (spectral_features, agent_state) are stripped from
the render output and optionally written to a sidecar metadata file.
"""

from __future__ import annotations
import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .scene import (
    AudioObjectNode,
    Frame,
    LFENode,
    LusidScene,
    SpectralFeaturesNode,
    AgentStateNode,
    time_to_seconds,
)


def _warn(msg: str) -> None:
    warnings.warn(f"[LUSID transcoder] {msg}", stacklevel=3)


# ---------------------------------------------------------------------------
# Core transcoder: LUSID → sonoPleth renderInstructions
# ---------------------------------------------------------------------------

def transcode_to_sonopleth(
    scene: LusidScene,
    output_sample_rate: int = 48000,
) -> Dict[str, Any]:
    """
    Convert a LusidScene into a sonoPleth-compatible renderInstructions dict.

    Parameters
    ----------
    scene : LusidScene
        Parsed LUSID scene.
    output_sample_rate : int
        Sample rate for the output JSON.  Defaults to 48000.

    Returns
    -------
    dict
        sonoPleth renderInstructions structure ready for json.dump().
    """
    sources: Dict[str, List[Dict[str, Any]]] = {}
    has_lfe = False

    # Use the scene's sample rate if available, otherwise the requested one
    sr = scene.sample_rate if scene.sample_rate else output_sample_rate

    # Track last-known position per audio_object group for hold behavior.
    # If an audio_object is absent from a frame, we carry forward its
    # last known cart (same as sonoPleth renderer hold-last-keyframe behavior).
    last_known_cart: Dict[int, List[float]] = {}

    for frame in scene.frames:
        # Convert frame time to seconds for output
        try:
            time_sec = time_to_seconds(frame.time, scene.time_unit, scene.sample_rate)
        except ValueError as e:
            _warn(f"Cannot convert frame time {frame.time}: {e}. Skipping frame.")
            continue

        # Collect which audio_object groups are present in this frame
        present_groups: set[int] = set()

        for node in frame.nodes:
            if isinstance(node, AudioObjectNode):
                group = node.group
                present_groups.add(group)
                last_known_cart[group] = list(node.cart)

                src_name = f"src_{group}"
                keyframe: Dict[str, Any] = {
                    "time": round(time_sec, 6),
                    "cart": [round(v, 6) for v in node.cart],
                }
                sources.setdefault(src_name, []).append(keyframe)

            elif isinstance(node, LFENode):
                has_lfe = True

    # Emit LFE entry: single keyframe at t=0 with no cart (matches sonoPleth convention)
    if has_lfe:
        sources["LFE"] = [{"time": 0.0}]

    # Build output
    output: Dict[str, Any] = {
        "sampleRate": sr,
        "timeUnit": "seconds",
        "sources": sources,
    }

    return output


# ---------------------------------------------------------------------------
# Metadata sidecar: spectral_features + agent_state
# ---------------------------------------------------------------------------

def extract_metadata_sidecar(scene: LusidScene) -> Dict[str, Any]:
    """
    Extract non-audio metadata (spectral_features, agent_state) into a
    sidecar dict, keyed by group → type → time-series.

    Structure:
    {
      "version": "0.5",
      "timeUnit": "seconds",
      "groups": {
        "1": {
          "spectral_features": [
            {"time": 0.0, "centroid": 5000.0, "flux": 0.15},
            ...
          ],
          "agent_state": [
            {"time": 0.0, "mood": "calm"},
            ...
          ]
        }
      }
    }
    """
    groups: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for frame in scene.frames:
        try:
            time_sec = time_to_seconds(frame.time, scene.time_unit, scene.sample_rate)
        except ValueError:
            continue

        for node in frame.nodes:
            if isinstance(node, (SpectralFeaturesNode, AgentStateNode)):
                group_key = str(node.group)
                type_key = node.type

                entry: Dict[str, Any] = {"time": round(time_sec, 6)}
                entry.update(node.data)

                groups.setdefault(group_key, {}).setdefault(type_key, []).append(entry)

    return {
        "version": scene.version,
        "timeUnit": "seconds",
        "groups": groups,
    }


# ---------------------------------------------------------------------------
# File I/O convenience
# ---------------------------------------------------------------------------

def transcode_file(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    sidecar_path: Optional[Union[str, Path]] = None,
    output_sample_rate: int = 48000,
) -> None:
    """
    End-to-end: parse a LUSID JSON file and write sonoPleth renderInstructions.

    Parameters
    ----------
    input_path : str or Path
        Input LUSID scene JSON.
    output_path : str or Path
        Output sonoPleth renderInstructions JSON.
    sidecar_path : str or Path or None
        If provided, write metadata sidecar (spectral_features, agent_state).
    output_sample_rate : int
        Sample rate for the output.
    """
    from .parser import parse_file

    scene = parse_file(input_path)

    # Render instructions
    render_json = transcode_to_sonopleth(scene, output_sample_rate)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(render_json, f, indent=2)

    src_count = len([k for k in render_json["sources"] if k != "LFE"])
    has_lfe = "LFE" in render_json["sources"]
    print(f"✓ Wrote renderInstructions: {output_path}")
    print(f"  {src_count} audio sources, LFE={'yes' if has_lfe else 'no'}, "
          f"sampleRate={render_json['sampleRate']}")

    # Metadata sidecar
    if sidecar_path is not None:
        sidecar = extract_metadata_sidecar(scene)
        sidecar_path = Path(sidecar_path)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sidecar_path, "w") as f:
            json.dump(sidecar, f, indent=2)
        group_count = len(sidecar["groups"])
        print(f"✓ Wrote metadata sidecar: {sidecar_path} ({group_count} groups)")
