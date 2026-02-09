"""
LUSID Scene v0.5 — Python package

Public API:
    from src import parse_file, parse_dict
    from src import adm_to_lusid_scene, write_lusid_scene
    from src.scene import LusidScene, Frame, AudioObjectNode, DirectSpeakerNode, LFENode, ...
"""

from .parser import parse_file, parse_dict
from .xmlParser import adm_to_lusid_scene, write_lusid_scene
from .scene import (
    LusidScene,
    Frame,
    AudioObjectNode,
    DirectSpeakerNode,
    LFENode,
    SpectralFeaturesNode,
    AgentStateNode,
)

__all__ = [
    "parse_file",
    "parse_dict",
    "adm_to_lusid_scene",
    "write_lusid_scene",
    "LusidScene",
    "Frame",
    "AudioObjectNode",
    "DirectSpeakerNode",
    "LFENode",
    "SpectralFeaturesNode",
    "AgentStateNode",
]
