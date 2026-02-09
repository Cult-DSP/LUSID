"""
LUSID Scene v0.5 — Python package

Public API:
    from src import parse_file, parse_dict
    from src import transcode_to_sonopleth, transcode_file, extract_metadata_sidecar
    from src.scene import LusidScene, Frame, AudioObjectNode, LFENode, ...
"""

from .parser import parse_file, parse_dict
from .transcoder import transcode_to_sonopleth, transcode_file, extract_metadata_sidecar
from .scene import (
    LusidScene,
    Frame,
    AudioObjectNode,
    LFENode,
    SpectralFeaturesNode,
    AgentStateNode,
)

__all__ = [
    "parse_file",
    "parse_dict",
    "transcode_to_sonopleth",
    "transcode_file",
    "extract_metadata_sidecar",
    "LusidScene",
    "Frame",
    "AudioObjectNode",
    "LFENode",
    "SpectralFeaturesNode",
    "AgentStateNode",
]
