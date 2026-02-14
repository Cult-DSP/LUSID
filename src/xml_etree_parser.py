"""
LUSID Scene v0.5 — ADM XML Parser (stdlib xml.etree.ElementTree)

Self-contained ADM XML parser using only Python standard library.
Parses bwfmetaedit conformance-point XML directly into LUSID scene format,
eliminating the need for lxml or intermediate JSON files.

This module replaces the combination of:
  - sonoPleth src/analyzeADM/parser.py (lxml-based, writes intermediate JSONs)
  - LUSID src/xmlParser.py adm_to_lusid_scene() (reads those JSONs)

With a single function:
  parse_adm_xml_to_lusid_scene(xml_path) → LusidScene

Created: 2026-02-10
Author: LUSID / sonoPleth Integration Team

TODO (future):
  - Create a scene summary / debug print function that works from LusidScene
    object directly, replacing the old analyzeMetadata.printSummary() flow.
"""

from __future__ import annotations
import json
import warnings
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .scene import (
    AudioObjectNode,
    DirectSpeakerNode,
    Frame,
    LFENode,
    LusidScene,
)


# ---------------------------------------------------------------------------
# Developer flags (synced with xmlParser.py)
# ---------------------------------------------------------------------------

_DEV_LFE_HARDCODED = True


# ---------------------------------------------------------------------------
# Namespace handling
# ---------------------------------------------------------------------------

# EBU ADM namespace — xml.etree.ElementTree prepends this as {ns}tagName
EBU_NS = "urn:ebu:metadata-schema:ebuCore_2016"
_NS_PREFIX = f"{{{EBU_NS}}}"


def _ebu(tag: str) -> str:
    """Return a namespace-qualified tag name for ElementTree lookups."""
    return f"{_NS_PREFIX}{tag}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _warn(msg: str) -> None:
    warnings.warn(f"[LUSID xml_etree_parser] {msg}", stacklevel=3)


def _parse_timecode_to_seconds(timecode: str) -> float:
    """Convert HH:MM:SS.SSSSS timecode to seconds."""
    try:
        hours, minutes, seconds = timecode.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (ValueError, AttributeError):
        _warn(f"Cannot parse timecode '{timecode}', defaulting to 0.0")
        return 0.0


def _get_position_coords(block_elem: ET.Element, ns_prefix: str) -> Tuple[float, float, float]:
    """Extract X, Y, Z coordinates from position elements within a block."""
    x, y, z = 0.0, 0.0, 0.0
    for pos in block_elem.findall(f"{ns_prefix}position"):
        coord = pos.attrib.get("coordinate", "")
        value = float(pos.text) if pos.text else 0.0
        if coord == "X":
            x = value
        elif coord == "Y":
            y = value
        elif coord == "Z":
            z = value
    return x, y, z


# ---------------------------------------------------------------------------
# Low-level extraction (mirrors sonoPleth parser.py functions)
# ---------------------------------------------------------------------------

def _find_ebu_root(tree: ET.ElementTree) -> Optional[ET.Element]:
    """Find the ebuCoreMain element within a bwfmetaedit conformance document.

    Handles two cases:
    1. The root IS the ebuCoreMain element (plain ADM XML)
    2. The root is a bwfmetaedit conformance_point_document with <aXML> wrapper
    """
    root = tree.getroot()

    # Case 1: root is ebuCoreMain directly
    if root.tag == _ebu("ebuCoreMain") or root.tag == "ebuCoreMain":
        return root

    # Case 2: bwfmetaedit wrapper — find <aXML> then look for ebuCoreMain inside
    axml = root.find(".//aXML")
    if axml is not None:
        # ebuCoreMain may be a direct child of <aXML>
        ebu_root = axml.find(_ebu("ebuCoreMain"))
        if ebu_root is not None:
            return ebu_root
        # Try without namespace (some exports omit it)
        ebu_root = axml.find("ebuCoreMain")
        if ebu_root is not None:
            return ebu_root

    # Fallback: search entire tree
    ebu_root = root.find(f".//{_ebu('ebuCoreMain')}")
    if ebu_root is not None:
        return ebu_root

    return None


def extract_global_data(tree: ET.ElementTree) -> Dict[str, str]:
    """Extract the <Technical> section from a bwfmetaedit conformance document.

    Returns a dict of tag → text for all children of <Technical>.
    Equivalent to sonoPleth parser.getGlobalData().
    """
    root = tree.getroot()
    technical = root.find(".//Technical")
    if technical is None:
        _warn("No <Technical> section found in XML")
        return {}

    global_data: Dict[str, str] = {}
    for elem in technical:
        tag = elem.tag.strip()
        text = elem.text.strip() if elem.text else ""
        global_data[tag] = text

    return global_data


def extract_direct_speaker_data(
    ebu_root: ET.Element,
) -> OrderedDict:
    """Extract DirectSpeaker channel data from EBU ADM XML.

    Returns an OrderedDict mapping channel name → speaker info dict.
    Equivalent to sonoPleth parser.getDirectSpeakerData().
    """
    direct_speakers: OrderedDict = OrderedDict()
    ns = _NS_PREFIX

    # Find all audioChannelFormat elements
    for channel in ebu_root.iter(_ebu("audioChannelFormat")):
        type_def = channel.attrib.get("typeDefinition", "")
        if type_def != "DirectSpeakers":
            continue

        channel_name = channel.attrib.get("audioChannelFormatName", "Unnamed")
        channel_id = channel.attrib.get("audioChannelFormatID", "")

        block = channel.find(f"{ns}audioBlockFormat")
        if block is None:
            continue

        x, y, z = _get_position_coords(block, ns)

        speaker_label_elem = block.find(f"{ns}speakerLabel")
        speaker_label = ""
        if speaker_label_elem is not None and speaker_label_elem.text:
            speaker_label = speaker_label_elem.text.strip()

        cartesian_elem = block.find(f"{ns}cartesian")
        cartesian = 1
        if cartesian_elem is not None and cartesian_elem.text:
            cartesian = int(cartesian_elem.text)

        direct_speakers[channel_name] = {
            "channelID": channel_id,
            "channelName": channel_name,
            "blockID": block.attrib.get("audioBlockFormatID", ""),
            "x": x,
            "y": y,
            "z": z,
            "speakerLabel": speaker_label,
            "cartesian": cartesian,
        }

    return direct_speakers


def extract_object_positions(
    ebu_root: ET.Element,
) -> OrderedDict:
    """Extract audio object position data from EBU ADM XML.

    Returns an OrderedDict mapping object name → list of position block dicts.
    Equivalent to sonoPleth parser.extractObjectPositions().
    """
    objects: OrderedDict = OrderedDict()
    ns = _NS_PREFIX

    for channel in ebu_root.iter(_ebu("audioChannelFormat")):
        type_def = channel.attrib.get("typeDefinition", "")
        if type_def != "Objects":
            continue

        name = channel.attrib.get("audioChannelFormatName", "Unnamed")
        channel_id = channel.attrib.get("audioChannelFormatID", "")

        blocks: List[Dict[str, Any]] = []
        for block in channel.findall(f"{ns}audioBlockFormat"):
            rtime = block.attrib.get("rtime", "00:00:00.00000")
            duration = block.attrib.get("duration", "00:00:00.00000")

            x, y, z = _get_position_coords(block, ns)

            position_data: Dict[str, Any] = {
                "rtime": rtime,
                "duration": duration,
                "x": x,
                "y": y,
                "z": z,
            }

            if channel_id:
                position_data["channelID"] = channel_id

            cartesian_elem = block.find(f"{ns}cartesian")
            if cartesian_elem is not None:
                position_data["cartesian"] = int(cartesian_elem.text) if cartesian_elem.text else 1

            width_elem = block.find(f"{ns}width")
            if width_elem is not None:
                position_data["width"] = float(width_elem.text) if width_elem.text else None

            depth_elem = block.find(f"{ns}depth")
            if depth_elem is not None:
                position_data["depth"] = float(depth_elem.text) if depth_elem.text else None

            height_elem = block.find(f"{ns}height")
            if height_elem is not None:
                position_data["height"] = float(height_elem.text) if height_elem.text else None

            blocks.append(position_data)

        if blocks:
            objects[name] = blocks

    return objects


# ---------------------------------------------------------------------------
# LFE detection (mirrors xmlParser.py)
# ---------------------------------------------------------------------------

def _is_lfe_channel(
    speaker_name: str,
    speaker_data: Dict[str, Any],
    channel_index_1based: int,
) -> bool:
    """Determine if a DirectSpeaker channel is LFE."""
    if _DEV_LFE_HARDCODED:
        return channel_index_1based == 4
    else:
        label = speaker_data.get("speakerLabel", "")
        name_lower = speaker_name.lower()
        return "lfe" in label.lower() or "lfe" in name_lower


# ---------------------------------------------------------------------------
# High-level: ADM XML → LUSID Scene (end-to-end)
# ---------------------------------------------------------------------------

def parse_adm_xml_to_lusid_scene(
    xml_path: Union[str, Path],
    contains_audio: Optional[Dict[str, Any]] = None,
) -> LusidScene:
    """
    Parse a bwfmetaedit ADM XML file directly into a LUSID scene.

    This is the main entry point — replaces the old multi-step pipeline of:
      parser.py → intermediate JSONs → xmlParser.adm_to_lusid_scene()

    Parameters
    ----------
    xml_path : str or Path
        Path to the bwfmetaedit conformance-point XML file
        (or a standalone EBU ADM XML file).
    contains_audio : dict or None
        Per-channel audio activity data (from checkAudioChannels).
        If None, all channels are assumed to contain audio.

    Returns
    -------
    LusidScene
        Complete LUSID scene with direct_speaker, audio_object, and LFE nodes.
    """
    if contains_audio is None:
        contains_audio = {}

    # -- Parse XML --
    tree = ET.parse(str(xml_path))

    # -- Extract global metadata (from <Technical> section) --
    global_data = extract_global_data(tree)
    sample_rate = int(global_data.get("SampleRate", 48000))
    duration_str = global_data.get("Duration", "")

    # -- Find EBU root for ADM content --
    ebu_root = _find_ebu_root(tree)
    if ebu_root is None:
        _warn("Could not find ebuCoreMain element in XML — returning empty scene")
        return LusidScene(version="0.5", sample_rate=sample_rate)

    # -- Extract ADM data --
    direct_speaker_data = extract_direct_speaker_data(ebu_root)
    object_data = extract_object_positions(ebu_root)

    # -- Build audio activity map (0-indexed) --
    audio_map: Dict[int, bool] = {}
    for channel_info in contains_audio.get("channels", []):
        idx = channel_info.get("channel_index")
        has_audio = channel_info.get("contains_audio", False)
        if idx is not None:
            audio_map[idx] = has_audio

    # -- Parse duration from ADM metadata --
    duration_seconds: Optional[float] = None
    if duration_str:
        try:
            duration_seconds = _parse_timecode_to_seconds(duration_str)
        except Exception as e:
            _warn(f"Could not parse duration '{duration_str}': {e}")

    # -- Metadata --
    metadata: Dict[str, Any] = {"sourceFormat": "ADM"}
    if duration_str:
        metadata["duration"] = duration_str
    if global_data.get("Format"):
        metadata["format"] = global_data["Format"]

    # =====================================================================
    # DIRECT SPEAKERS → single frame at t=0 (static position)
    # =====================================================================
    group_counter = 1
    num_direct_speakers = len(direct_speaker_data)
    static_nodes: list = []
    channel_1based = 0

    for speaker_name, speaker_info in direct_speaker_data.items():
        channel_1based += 1
        group_id = channel_1based

        # Check if channel has audio (0-indexed in audio_map)
        if not audio_map.get(channel_1based - 1, True):
            continue

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

    group_counter = num_direct_speakers + 1

    # =====================================================================
    # AUDIO OBJECTS → frames with time-varying positions
    # =====================================================================
    time_to_nodes: Dict[float, List] = {}

    # Add static nodes to t=0 frame
    time_to_nodes.setdefault(0.0, []).extend(static_nodes)

    for obj_name, blocks in object_data.items():
        if not blocks:
            continue

        obj_group = group_counter
        group_counter += 1

        # Channel index for audio activity check
        obj_channel_0based = num_direct_speakers + (obj_group - num_direct_speakers - 1)
        if not audio_map.get(obj_channel_0based, True):
            continue

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
        duration=duration_seconds,  # Set explicit duration from ADM
        frames=frames,
        time_unit="seconds",
        sample_rate=sample_rate,
        metadata=metadata,
    )

    return scene


# ---------------------------------------------------------------------------
# File I/O convenience
# ---------------------------------------------------------------------------

def parse_and_write_lusid_scene(
    xml_path: Union[str, Path],
    output_path: Union[str, Path],
    contains_audio: Optional[Dict[str, Any]] = None,
) -> LusidScene:
    """
    End-to-end: Parse ADM XML → build LUSID scene → write to disk.

    Parameters
    ----------
    xml_path : str or Path
        Path to bwfmetaedit conformance-point XML.
    output_path : str or Path
        Where to write the LUSID scene JSON.
    contains_audio : dict or None
        Per-channel audio activity data.

    Returns
    -------
    LusidScene
    """
    scene = parse_adm_xml_to_lusid_scene(xml_path, contains_audio)
    write_lusid_scene(scene, output_path)
    return scene


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
