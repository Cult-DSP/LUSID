"""
LUSID Scene v0.5 — ADM XML Parser

Converts pre-parsed ADM data (from sonoPleth's parser.py) into a LUSID scene.

This module accepts Python dicts already extracted from ADM XML by sonoPleth's
existing lxml-based parser. It does NOT parse XML directly — keeping LUSID
free of external dependencies.

DEV NOTE (2026-02-09): Future pipeline evaluation needed:
  - Option A: Add lxml dependency to LUSID for direct XML parsing
  - Option B: Use Python stdlib xml.etree.ElementTree (no dependency)
  - Option C: Keep current dict-based approach (current)
  Decision deferred until real-world usage patterns are established.

Usage from sonoPleth pipeline:
    from LUSID.src import adm_to_lusid_scene, write_lusid_scene

    scene = adm_to_lusid_scene(
        object_data=objectData,           # from parser.extractObjectPositions()
        direct_speaker_data=directSpeakerData,  # from parser.getDirectSpeakerData()
        global_data=globalData,           # from parser.getGlobalData()
        contains_audio=containsAudio,     # from checkAudioChannels.exportAudioActivity()
    )
    write_lusid_scene(scene, "processedData/stageForRender/scene.lusid.json")
"""

from __future__ import annotations
import json
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .scene import (
    AudioObjectNode,
    DirectSpeakerNode,
    Frame,
    LFENode,
    LusidScene,
)


# ---------------------------------------------------------------------------
# Developer flags
# ---------------------------------------------------------------------------

# When True: LFE is detected as the 4th DirectSpeaker (hardcoded index).
# When False: LFE is detected by checking speakerLabel for "LFE" substring.
# TODO: Set to False once label-based detection is tested with diverse ADM sources.
_DEV_LFE_HARDCODED = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _warn(msg: str) -> None:
    warnings.warn(f"[LUSID xmlParser] {msg}", stacklevel=3)


def _parse_timecode_to_seconds(timecode: str) -> float:
    """Convert HH:MM:SS.SSSSS timecode to seconds."""
    try:
        hours, minutes, seconds = timecode.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (ValueError, AttributeError):
        _warn(f"Cannot parse timecode '{timecode}', defaulting to 0.0")
        return 0.0


def _build_channel_audio_map(contains_audio: Dict[str, Any]) -> Dict[int, bool]:
    """Build a mapping of channel_index → contains_audio from containsAudio data."""
    audio_map: Dict[int, bool] = {}
    for channel_info in contains_audio.get("channels", []):
        idx = channel_info.get("channel_index")
        has_audio = channel_info.get("contains_audio", False)
        if idx is not None:
            audio_map[idx] = has_audio
    return audio_map


def _is_lfe_channel(
    speaker_name: str,
    speaker_data: Dict[str, Any],
    channel_index_1based: int,
) -> bool:
    """Determine if a DirectSpeaker channel is LFE.

    Uses _DEV_LFE_HARDCODED flag to choose detection method.
    """
    if _DEV_LFE_HARDCODED:
        return channel_index_1based == 4
    else:
        # Future: label-based detection
        label = speaker_data.get("speakerLabel", "")
        name_lower = speaker_name.lower()
        return "lfe" in label.lower() or "lfe" in name_lower


# ---------------------------------------------------------------------------
# Core: ADM dicts → LUSID scene
# ---------------------------------------------------------------------------

def adm_to_lusid_scene(
    object_data: Dict[str, List[Dict[str, Any]]],
    direct_speaker_data: Dict[str, Dict[str, Any]],
    global_data: Optional[Dict[str, str]] = None,
    contains_audio: Optional[Dict[str, Any]] = None,
) -> LusidScene:
    """
    Convert pre-parsed ADM data into a LUSID scene.

    Parameters
    ----------
    object_data : dict
        From sonoPleth parser.extractObjectPositions().
        Maps object name → list of position blocks with rtime, duration, x, y, z.
    direct_speaker_data : dict
        From sonoPleth parser.getDirectSpeakerData().
        Maps speaker name → dict with x, y, z, speakerLabel, channelID.
    global_data : dict or None
        From sonoPleth parser.getGlobalData().
        Contains SampleRate, Duration, Channels, etc.
    contains_audio : dict or None
        From sonoPleth checkAudioChannels.exportAudioActivity().
        Per-channel audio detection results.

    Returns
    -------
    LusidScene
        Complete LUSID scene with direct_speaker, audio_object, and LFE nodes.
    """
    if global_data is None:
        global_data = {}
    if contains_audio is None:
        contains_audio = {}

    # -- Extract global metadata --
    sample_rate = int(global_data.get("SampleRate", 48000))
    duration_str = global_data.get("Duration", "")

    # -- Build audio activity map (0-indexed) --
    audio_map = _build_channel_audio_map(contains_audio)

    # -- Build metadata --
    metadata: Dict[str, Any] = {
        "sourceFormat": "ADM",
    }
    if duration_str:
        metadata["duration"] = duration_str
    if global_data.get("Format"):
        metadata["format"] = global_data["Format"]

    # -- Group assignment --
    # DirectSpeakers: groups 1–N (in order of appearance)
    # Audio Objects: groups (N+1)+ (in order of appearance)
    group_counter = 1
    num_direct_speakers = len(direct_speaker_data)

    # =====================================================================
    # DIRECT SPEAKERS → single frame at t=0 (static position)
    # =====================================================================
    static_nodes: list = []
    channel_1based = 0

    for speaker_name, speaker_info in direct_speaker_data.items():
        channel_1based += 1
        group_id = channel_1based  # Groups 1, 2, 3, ... for DirectSpeakers

        # Check if channel has audio (0-indexed in audio_map)
        if not audio_map.get(channel_1based - 1, True):
            continue  # Skip silent channels

        # LFE detection
        if _is_lfe_channel(speaker_name, speaker_info, channel_1based):
            static_nodes.append(LFENode(id=f"{group_id}.1"))
            continue

        # Normal DirectSpeaker
        cart = [
            float(speaker_info.get("x", 0.0)),
            float(speaker_info.get("y", 0.0)),
            float(speaker_info.get("z", 0.0)),
        ]
        static_nodes.append(DirectSpeakerNode(
            id=f"{group_id}.1",
            cart=cart,
            speakerLabel=speaker_info.get("speakerLabel", ""),
            channelID=speaker_info.get("channelID", ""),
        ))

    group_counter = num_direct_speakers + 1  # Objects start after DirectSpeakers

    # =====================================================================
    # AUDIO OBJECTS → one or more frames with time-varying positions
    # =====================================================================

    # Collect all unique timestamps across all objects
    time_to_nodes: Dict[float, List] = {}

    # Add static nodes to t=0 frame
    time_to_nodes.setdefault(0.0, []).extend(static_nodes)

    obj_name_to_group: Dict[str, int] = {}

    for obj_name, blocks in object_data.items():
        if not blocks:
            continue

        # Assign group ID
        obj_group = group_counter
        obj_name_to_group[obj_name] = obj_group
        group_counter += 1

        # Determine channel index for this object
        # Objects follow DirectSpeakers in channel order
        obj_channel_0based = num_direct_speakers + (obj_group - num_direct_speakers - 1)

        # Check if channel has audio
        if not audio_map.get(obj_channel_0based, True):
            continue  # Skip silent channels

        for block in blocks:
            time_sec = _parse_timecode_to_seconds(block.get("rtime", "00:00:00.00000"))
            cart = [
                float(block.get("x", 0.0)),
                float(block.get("y", 0.0)),
                float(block.get("z", 0.0)),
            ]
            node = AudioObjectNode(
                id=f"{obj_group}.1",
                cart=cart,
            )
            time_to_nodes.setdefault(time_sec, []).append(node)

    # =====================================================================
    # BUILD FRAMES
    # =====================================================================

    frames: List[Frame] = []
    for time_val in sorted(time_to_nodes.keys()):
        nodes = time_to_nodes[time_val]
        if nodes:
            frames.append(Frame(time=round(time_val, 6), nodes=nodes))

    scene = LusidScene(
        version="0.5",
        frames=frames,
        time_unit="seconds",
        sample_rate=sample_rate,
        metadata=metadata,
    )

    return scene


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def write_lusid_scene(
    scene: LusidScene,
    output_path: Union[str, Path],
) -> Path:
    """
    Serialize a LusidScene to JSON file.

    Parameters
    ----------
    scene : LusidScene
        The scene to write.
    output_path : str or Path
        Output file path.

    Returns
    -------
    Path
        The resolved output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(scene.to_dict(), f, indent=2)

    # Summary
    num_audio = len(scene.audio_object_groups())
    num_ds = len(scene.direct_speaker_groups())
    has_lfe = scene.has_lfe()
    print(f"✓ Wrote LUSID scene: {output_path}")
    print(f"  {num_ds} direct_speaker, {num_audio} audio_object, "
          f"LFE={'yes' if has_lfe else 'no'}, "
          f"sampleRate={scene.sample_rate}, "
          f"{scene.frame_count} frames")

    return output_path


def load_processed_data_and_build_scene(
    processed_dir: str = "processedData",
    output_path: str = "processedData/stageForRender/scene.lusid.json",
) -> LusidScene:
    """
    Convenience function: load all intermediate JSONs and build + write LUSID scene.

    This reads the same intermediate files that createRenderInfo.py used to read:
    - objectData.json
    - directSpeakerData.json
    - globalData.json
    - containsAudio.json

    Parameters
    ----------
    processed_dir : str
        Directory containing the intermediate JSON files.
    output_path : str
        Where to write the LUSID scene JSON.

    Returns
    -------
    LusidScene
    """
    import os

    def _load_json(filename: str) -> dict:
        path = os.path.join(processed_dir, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        else:
            _warn(f"{path} not found, using empty dict")
            return {}

    object_data = _load_json("objectData.json")
    direct_speaker_data = _load_json("directSpeakerData.json")
    global_data = _load_json("globalData.json")
    contains_audio = _load_json("containsAudio.json")

    scene = adm_to_lusid_scene(
        object_data=object_data,
        direct_speaker_data=direct_speaker_data,
        global_data=global_data,
        contains_audio=contains_audio,
    )

    write_lusid_scene(scene, output_path)
    return scene
