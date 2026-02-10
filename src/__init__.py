"""
LUSID Scene v0.5 — Python package

Public API:
  - parse_file(): Load LUSID JSON file → LusidScene
  - parse_dict(): Load LUSID dict → LusidScene
  - parse_adm_xml_to_lusid_scene(): Parse ADM XML → LusidScene (stdlib only)
  - parse_and_write_lusid_scene(): Parse ADM XML and write LUSID JSON

Data Model:
  - LusidScene: Main scene container
  - Frame: Time-based data container
  - AudioObjectNode: Spatial audio object
  - DirectSpeakerNode: Fixed-position speaker channel
  - LFENode: Low-frequency effects
  - SpectralFeaturesNode: Analysis data
  - AgentStateNode: AI/agent metadata
"""

from .parser import parse_file, parse_dict
from .xml_etree_parser import parse_adm_xml_to_lusid_scene, parse_and_write_lusid_scene
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
    "parse_adm_xml_to_lusid_scene",
    "parse_and_write_lusid_scene",
    "LusidScene",
    "Frame",
    "AudioObjectNode",
    "DirectSpeakerNode",
    "LFENode",
    "SpectralFeaturesNode",
    "AgentStateNode",
]
