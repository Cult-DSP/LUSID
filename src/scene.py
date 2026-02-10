"""
LUSID Scene v0.5 — Data Model

Dataclass representations of the LUSID scene graph:
  LusidScene → Frame[] → Node[]

Node types:
  - AudioObjectNode  (type="audio_object")  — spatial source with cart [x,y,z]
  - DirectSpeakerNode (type="direct_speaker") — fixed bed channel with position + label
  - LFENode          (type="LFE")           — low-frequency effects, no position
  - SpectralFeaturesNode (type="spectral_features") — analysis data
  - AgentStateNode   (type="agent_state")   — AI/agent metadata
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union


# ---------------------------------------------------------------------------
# Time-unit helpers
# ---------------------------------------------------------------------------

TIMEUNIT_ALIASES = {
    "seconds": "seconds",
    "s": "seconds",
    "samples": "samples",
    "samp": "samples",
    "milliseconds": "milliseconds",
    "ms": "milliseconds",
}


def normalize_time_unit(raw: str) -> str:
    """Resolve aliases to canonical time-unit string."""
    canonical = TIMEUNIT_ALIASES.get(raw.lower().strip())
    if canonical is None:
        raise ValueError(f"Unknown timeUnit '{raw}'. "
                         f"Expected one of: {list(TIMEUNIT_ALIASES.keys())}")
    return canonical


def time_to_seconds(value: float, time_unit: str, sample_rate: Optional[int]) -> float:
    """Convert a timestamp to seconds."""
    if time_unit == "seconds":
        return value
    elif time_unit == "milliseconds":
        return value * 0.001
    elif time_unit == "samples":
        if sample_rate is None or sample_rate <= 0:
            raise ValueError("sampleRate required when timeUnit is 'samples'")
        return value / float(sample_rate)
    else:
        raise ValueError(f"Cannot convert timeUnit '{time_unit}' to seconds")


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------

@dataclass
class AudioObjectNode:
    """A spatial audio source with a Cartesian direction vector."""
    id: str                       # e.g. "1.1"
    cart: List[float]             # [x, y, z]
    gain: float = 1.0            # optional per-object gain

    @property
    def type(self) -> str:
        return "audio_object"

    @property
    def group(self) -> int:
        """Group number (X in X.Y)."""
        return int(self.id.split(".")[0])

    @property
    def hierarchy(self) -> int:
        """Hierarchy level (Y in X.Y)."""
        return int(self.id.split(".")[1])

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "type": self.type, "cart": list(self.cart)}
        if self.gain != 1.0:
            d["gain"] = self.gain
        return d


@dataclass
class DirectSpeakerNode:
    """A fixed-position bed channel (e.g., L, R, C, Lss, Rss, etc.).

    Treated by the renderer as an audio_object with a single keyframe.
    The speakerLabel and channelID are informational metadata.
    """
    id: str                       # e.g. "1.1"
    cart: List[float]             # [x, y, z]
    speakerLabel: str = ""        # e.g. "RC_L", "RC_Rss"
    channelID: str = ""           # e.g. "AC_00011001"

    @property
    def type(self) -> str:
        return "direct_speaker"

    @property
    def group(self) -> int:
        """Group number (X in X.Y)."""
        return int(self.id.split(".")[0])

    @property
    def hierarchy(self) -> int:
        """Hierarchy level (Y in X.Y)."""
        return int(self.id.split(".")[1])

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "cart": list(self.cart),
        }
        if self.speakerLabel:
            d["speakerLabel"] = self.speakerLabel
        if self.channelID:
            d["channelID"] = self.channelID
        return d


@dataclass
class LFENode:
    """Low-frequency effects node — routed directly to subwoofers, not spatialized."""
    id: str

    @property
    def type(self) -> str:
        return "LFE"

    @property
    def group(self) -> int:
        return int(self.id.split(".")[0])

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type}


@dataclass
class SpectralFeaturesNode:
    """Spectral analysis data attached to a parent audio_object."""
    id: str
    data: Dict[str, Any] = field(default_factory=dict)
    # data may contain: centroid, flux, bandwidth, etc.

    @property
    def type(self) -> str:
        return "spectral_features"

    @property
    def group(self) -> int:
        return int(self.id.split(".")[0])

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "type": self.type}
        d.update(self.data)
        return d


@dataclass
class AgentStateNode:
    """AI / agent state metadata attached to a parent audio_object."""
    id: str
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def type(self) -> str:
        return "agent_state"

    @property
    def group(self) -> int:
        return int(self.id.split(".")[0])

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"id": self.id, "type": self.type}
        d.update(self.data)
        return d


# Union of all node types
Node = Union[AudioObjectNode, DirectSpeakerNode, LFENode, SpectralFeaturesNode, AgentStateNode]


# ---------------------------------------------------------------------------
# Frame & Scene
# ---------------------------------------------------------------------------

@dataclass
class Frame:
    """A single timestep snapshot containing all active nodes."""
    time: float          # in the scene's declared timeUnit
    nodes: List[Node] = field(default_factory=list)

    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        return [n for n in self.nodes if n.type == node_type]

    def get_nodes_by_group(self, group_id: int) -> List[Node]:
        return [n for n in self.nodes if n.group == group_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "nodes": [n.to_dict() for n in self.nodes],
        }


@dataclass
class LusidScene:
    """
    Top-level LUSID Scene v0.5 container.

    Attributes
    ----------
    version : str
        Schema version ("0.5").
    frames : list[Frame]
        Time-ordered scene snapshots.
    time_unit : str
        Canonical time unit ("seconds", "samples", or "milliseconds").
    sample_rate : int or None
        Sample rate in Hz. Required when time_unit == "samples".
    metadata : dict
        Optional top-level metadata (title, author, notes, etc.).
    """
    version: str = "0.5"
    frames: List[Frame] = field(default_factory=list)
    time_unit: str = "seconds"
    sample_rate: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- Queries --

    @property
    def duration(self) -> float:
        """Duration in the scene's declared time unit (last frame time)."""
        if not self.frames:
            return 0.0
        return self.frames[-1].time

    @property
    def duration_seconds(self) -> float:
        """Duration converted to seconds."""
        return time_to_seconds(self.duration, self.time_unit, self.sample_rate)

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def audio_object_groups(self) -> List[int]:
        """Return sorted list of unique group IDs that contain audio_object nodes."""
        groups: set[int] = set()
        for frame in self.frames:
            for node in frame.get_nodes_by_type("audio_object"):
                groups.add(node.group)
        return sorted(groups)

    def direct_speaker_groups(self) -> List[int]:
        """Return sorted list of unique group IDs that contain direct_speaker nodes."""
        groups: set[int] = set()
        for frame in self.frames:
            for node in frame.get_nodes_by_type("direct_speaker"):
                groups.add(node.group)
        return sorted(groups)

    def has_lfe(self) -> bool:
        """Return True if any frame contains an LFE node."""
        return any(
            frame.get_nodes_by_type("LFE")
            for frame in self.frames
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "version": self.version,
            "timeUnit": self.time_unit,
            "frames": [f.to_dict() for f in self.frames],
        }
        if self.sample_rate is not None:
            d["sampleRate"] = self.sample_rate
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    def summary(self) -> None:
        """Print a human-readable summary of the scene contents."""
        print(f"LUSID Scene v{self.version}")
        print(f"  Duration: {self.duration:.3f} {self.time_unit}")
        if self.sample_rate:
            print(f"  Sample Rate: {self.sample_rate} Hz")
        print(f"  Frames: {self.frame_count}")
        
        # Count nodes by type across all frames
        node_counts = {}
        for frame in self.frames:
            for node in frame.nodes:
                node_type = type(node).__name__.replace('Node', '').lower()
                node_counts[node_type] = node_counts.get(node_type, 0) + 1
        
        if node_counts:
            print("  Nodes:")
            for node_type, count in sorted(node_counts.items()):
                print(f"    {node_type}: {count}")
        
        # Show group info
        audio_groups = self.audio_object_groups()
        ds_groups = self.direct_speaker_groups()
        if audio_groups:
            print(f"  Audio Object Groups: {audio_groups}")
        if ds_groups:
            print(f"  Direct Speaker Groups: {ds_groups}")
        if self.has_lfe():
            print("  LFE: present")
