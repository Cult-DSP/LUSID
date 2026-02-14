"""
Tests for LUSID Scene v0.5 — Parser & Data Model
stdlib only — no external dependencies
"""

import math
import sys
import unittest
import warnings
from pathlib import Path

# Allow imports from LUSID/src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scene import (
    AudioObjectNode,
    DirectSpeakerNode,
    LFENode,
    SpectralFeaturesNode,
    AgentStateNode,
    Frame,
    LusidScene,
    normalize_time_unit,
    time_to_seconds,
)
from src.parser import parse_dict, parse_file


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_SCENE = FIXTURE_DIR / "sample_scene_v0.5.json"


# ---------------------------------------------------------------------------
# scene.py unit tests
# ---------------------------------------------------------------------------

class TestTimeUnit(unittest.TestCase):
    def test_normalize_aliases(self):
        self.assertEqual(normalize_time_unit("seconds"), "seconds")
        self.assertEqual(normalize_time_unit("s"), "seconds")
        self.assertEqual(normalize_time_unit("samples"), "samples")
        self.assertEqual(normalize_time_unit("samp"), "samples")
        self.assertEqual(normalize_time_unit("milliseconds"), "milliseconds")
        self.assertEqual(normalize_time_unit("ms"), "milliseconds")

    def test_normalize_case_insensitive(self):
        self.assertEqual(normalize_time_unit("Seconds"), "seconds")
        self.assertEqual(normalize_time_unit("MS"), "milliseconds")

    def test_normalize_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_time_unit("ticks")

    def test_to_seconds(self):
        self.assertEqual(time_to_seconds(1.5, "seconds", None), 1.5)
        self.assertAlmostEqual(time_to_seconds(1500.0, "milliseconds", None), 1.5)
        self.assertAlmostEqual(time_to_seconds(48000.0, "samples", 48000), 1.0)

    def test_to_seconds_samples_no_sr(self):
        with self.assertRaises(ValueError):
            time_to_seconds(48000.0, "samples", None)


class TestNodeModels(unittest.TestCase):
    def test_audio_object_basics(self):
        n = AudioObjectNode(id="1.1", cart=[0.0, 1.0, 0.0])
        self.assertEqual(n.type, "audio_object")
        self.assertEqual(n.group, 1)
        self.assertEqual(n.hierarchy, 1)
        self.assertEqual(n.gain, 1.0)

    def test_audio_object_to_dict(self):
        n = AudioObjectNode(id="2.1", cart=[0.5, 0.5, 0.0], gain=0.8)
        d = n.to_dict()
        self.assertEqual(d["id"], "2.1")
        self.assertEqual(d["type"], "audio_object")
        self.assertEqual(d["cart"], [0.5, 0.5, 0.0])
        self.assertEqual(d["gain"], 0.8)

    def test_audio_object_default_gain_omitted(self):
        n = AudioObjectNode(id="1.1", cart=[0.0, 1.0, 0.0])
        d = n.to_dict()
        self.assertNotIn("gain", d)

    def test_lfe_node(self):
        n = LFENode(id="3.1")
        self.assertEqual(n.type, "LFE")
        self.assertEqual(n.group, 3)
        self.assertEqual(n.to_dict(), {"id": "3.1", "type": "LFE"})

    def test_spectral_features_node(self):
        n = SpectralFeaturesNode(id="1.2", data={"centroid": 5000.0, "flux": 0.15})
        self.assertEqual(n.type, "spectral_features")
        self.assertEqual(n.group, 1)
        d = n.to_dict()
        self.assertEqual(d["centroid"], 5000.0)

    def test_agent_state_node(self):
        n = AgentStateNode(id="2.2", data={"mood": "calm"})
        self.assertEqual(n.type, "agent_state")
        d = n.to_dict()
        self.assertEqual(d["mood"], "calm")

    def test_direct_speaker_basics(self):
        n = DirectSpeakerNode(id="1.1", cart=[-1.0, 1.0, 0.0], speakerLabel="RC_L", channelID="AC_00011001")
        self.assertEqual(n.type, "direct_speaker")
        self.assertEqual(n.group, 1)
        self.assertEqual(n.hierarchy, 1)
        self.assertEqual(n.speakerLabel, "RC_L")
        self.assertEqual(n.channelID, "AC_00011001")

    def test_direct_speaker_to_dict(self):
        n = DirectSpeakerNode(id="2.1", cart=[1.0, 1.0, 0.0], speakerLabel="RC_R")
        d = n.to_dict()
        self.assertEqual(d["id"], "2.1")
        self.assertEqual(d["type"], "direct_speaker")
        self.assertEqual(d["cart"], [1.0, 1.0, 0.0])
        self.assertEqual(d["speakerLabel"], "RC_R")
        self.assertNotIn("channelID", d)  # empty string omitted

    def test_direct_speaker_defaults(self):
        n = DirectSpeakerNode(id="5.1", cart=[0.0, 0.0, 1.0])
        self.assertEqual(n.speakerLabel, "")
        self.assertEqual(n.channelID, "")


class TestFrame(unittest.TestCase):
    def test_get_nodes_by_type(self):
        f = Frame(time=0.0, nodes=[
            AudioObjectNode(id="1.1", cart=[0, 1, 0]),
            DirectSpeakerNode(id="5.1", cart=[-1, 1, 0], speakerLabel="RC_L"),
            LFENode(id="3.1"),
            AudioObjectNode(id="2.1", cart=[1, 0, 0]),
        ])
        self.assertEqual(len(f.get_nodes_by_type("audio_object")), 2)
        self.assertEqual(len(f.get_nodes_by_type("direct_speaker")), 1)
        self.assertEqual(len(f.get_nodes_by_type("LFE")), 1)
        self.assertEqual(len(f.get_nodes_by_type("agent_state")), 0)

    def test_get_nodes_by_group(self):
        f = Frame(time=0.0, nodes=[
            AudioObjectNode(id="1.1", cart=[0, 1, 0]),
            SpectralFeaturesNode(id="1.2", data={"centroid": 5000}),
            AudioObjectNode(id="2.1", cart=[1, 0, 0]),
        ])
        group1 = f.get_nodes_by_group(1)
        self.assertEqual(len(group1), 2)


class TestLusidScene(unittest.TestCase):
    def test_empty_scene(self):
        s = LusidScene()
        self.assertEqual(s.calculated_duration, 0.0)
        self.assertEqual(s.duration_seconds, 0.0)  # Should also be 0 when no explicit duration
        self.assertEqual(s.frame_count, 0)
        self.assertEqual(s.audio_object_groups(), [])
        self.assertFalse(s.has_lfe())

    def test_scene_with_frames(self):
        s = LusidScene(frames=[
            Frame(time=0.0, nodes=[
                DirectSpeakerNode(id="1.1", cart=[-1, 1, 0], speakerLabel="RC_L"),
                AudioObjectNode(id="11.1", cart=[0, 1, 0]),
                LFENode(id="4.1"),
            ]),
            Frame(time=2.0, nodes=[
                AudioObjectNode(id="11.1", cart=[1, 0, 0]),
                AudioObjectNode(id="12.1", cart=[0, 0, 1]),
            ]),
        ])
        self.assertEqual(s.calculated_duration, 2.0)
        self.assertEqual(s.duration_seconds, 2.0)  # Should use calculated when no explicit
        self.assertEqual(s.frame_count, 2)
        self.assertEqual(s.audio_object_groups(), [11, 12])
        self.assertEqual(s.direct_speaker_groups(), [1])
        self.assertTrue(s.has_lfe())

    def test_explicit_duration(self):
        """Test that explicit duration takes precedence over calculated duration."""
        s = LusidScene(
            duration=300.0,  # 5 minutes explicit
            frames=[
                Frame(time=0.0, nodes=[AudioObjectNode(id="11.1", cart=[0, 1, 0])]),
                Frame(time=2.0, nodes=[AudioObjectNode(id="11.1", cart=[1, 0, 0])]),
            ]
        )
        self.assertEqual(s.calculated_duration, 2.0)  # Calculated from frames
        self.assertEqual(s.duration, 300.0)           # Explicit duration
        self.assertEqual(s.duration_seconds, 300.0)  # Should use explicit


# ---------------------------------------------------------------------------
# parser.py unit tests
# ---------------------------------------------------------------------------

class TestParserBasic(unittest.TestCase):
    def test_minimal_valid(self):
        raw = {
            "version": "0.5",
            "frames": [
                {"time": 0.0, "nodes": [
                    {"id": "1.1", "type": "audio_object", "cart": [0, 1, 0]}
                ]}
            ]
        }
        scene = parse_dict(raw)
        self.assertEqual(scene.version, "0.5")
        self.assertEqual(scene.frame_count, 1)
        self.assertEqual(len(scene.frames[0].nodes), 1)
        self.assertIsInstance(scene.frames[0].nodes[0], AudioObjectNode)

    def test_missing_version_warns(self):
        raw = {"frames": [{"time": 0.0, "nodes": []}]}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            scene = parse_dict(raw)
            self.assertTrue(any("version" in str(x.message) for x in w))
        self.assertEqual(scene.version, "0.5")

    def test_missing_frames_warns(self):
        raw = {"version": "0.5"}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            scene = parse_dict(raw)
            self.assertTrue(any("frames" in str(x.message) for x in w))
        self.assertEqual(scene.frame_count, 0)

    def test_frames_sorted_by_time(self):
        raw = {
            "version": "0.5",
            "frames": [
                {"time": 2.0, "nodes": []},
                {"time": 0.5, "nodes": []},
                {"time": 1.0, "nodes": []},
            ]
        }
        scene = parse_dict(raw)
        times = [f.time for f in scene.frames]
        self.assertEqual(times, [0.5, 1.0, 2.0])

    def test_time_unit_parsing(self):
        raw = {"version": "0.5", "timeUnit": "ms", "frames": []}
        scene = parse_dict(raw)
        self.assertEqual(scene.time_unit, "milliseconds")

    def test_invalid_time_unit_falls_back(self):
        raw = {"version": "0.5", "timeUnit": "ticks", "frames": []}
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.time_unit, "seconds")

    def test_sample_rate_parsed(self):
        raw = {"version": "0.5", "sampleRate": 44100, "frames": []}
        scene = parse_dict(raw)
        self.assertEqual(scene.sample_rate, 44100)

    def test_metadata_parsed(self):
        raw = {"version": "0.5", "metadata": {"title": "Test"}, "frames": []}
        scene = parse_dict(raw)
        self.assertEqual(scene.metadata["title"], "Test")


class TestParserNodeValidation(unittest.TestCase):
    def test_missing_node_id_warns(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"type": "audio_object", "cart": [0, 1, 0]}
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.frames[0].nodes, [])

    def test_invalid_node_id_warns(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "bad", "type": "audio_object", "cart": [0, 1, 0]}
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.frames[0].nodes, [])

    def test_missing_cart_warns(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "audio_object"}
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.frames[0].nodes, [])

    def test_nan_cart_warns(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "audio_object", "cart": [float("nan"), 1.0, 0.0]}
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.frames[0].nodes, [])

    def test_duplicate_node_id_keeps_last(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "audio_object", "cart": [0, 1, 0]},
                {"id": "1.1", "type": "audio_object", "cart": [1, 0, 0]},
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(len(scene.frames[0].nodes), 1)
        self.assertEqual(scene.frames[0].nodes[0].cart, [1.0, 0.0, 0.0])

    def test_unknown_type_warns(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "unknown_thing"}
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.frames[0].nodes, [])

    def test_lfe_node_parsed(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "3.1", "type": "LFE"}
            ]}]
        }
        scene = parse_dict(raw)
        self.assertEqual(len(scene.frames[0].nodes), 1)
        self.assertIsInstance(scene.frames[0].nodes[0], LFENode)

    def test_spectral_features_parsed(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.2", "type": "spectral_features", "centroid": 5000, "flux": 0.1}
            ]}]
        }
        scene = parse_dict(raw)
        node = scene.frames[0].nodes[0]
        self.assertIsInstance(node, SpectralFeaturesNode)
        self.assertEqual(node.data["centroid"], 5000)

    def test_agent_state_parsed(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "2.2", "type": "agent_state", "mood": "calm", "intensity": 0.3}
            ]}]
        }
        scene = parse_dict(raw)
        node = scene.frames[0].nodes[0]
        self.assertIsInstance(node, AgentStateNode)
        self.assertEqual(node.data["mood"], "calm")
        self.assertEqual(node.data["intensity"], 0.3)

    def test_direct_speaker_parsed(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "direct_speaker", "cart": [-1.0, 1.0, 0.0],
                 "speakerLabel": "RC_L", "channelID": "AC_00011001"}
            ]}]
        }
        scene = parse_dict(raw)
        node = scene.frames[0].nodes[0]
        self.assertIsInstance(node, DirectSpeakerNode)
        self.assertEqual(node.cart, [-1.0, 1.0, 0.0])
        self.assertEqual(node.speakerLabel, "RC_L")
        self.assertEqual(node.channelID, "AC_00011001")

    def test_direct_speaker_missing_cart_warns(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "direct_speaker", "speakerLabel": "RC_L"}
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.frames[0].nodes, [])

    def test_direct_speaker_nan_cart_warns(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "direct_speaker", "cart": [float("nan"), 1.0, 0.0]}
            ]}]
        }
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scene = parse_dict(raw)
        self.assertEqual(scene.frames[0].nodes, [])


class TestParserFixture(unittest.TestCase):
    def test_sample_scene_loads(self):
        scene = parse_file(SAMPLE_SCENE)
        self.assertEqual(scene.version, "0.5")
        self.assertEqual(scene.sample_rate, 48000)
        self.assertEqual(scene.time_unit, "seconds")
        self.assertEqual(scene.frame_count, 5)
        self.assertEqual(scene.audio_object_groups(), [11, 12])
        self.assertEqual(scene.direct_speaker_groups(), [1, 2, 3])
        self.assertTrue(scene.has_lfe())

    def test_sample_scene_frames_sorted(self):
        scene = parse_file(SAMPLE_SCENE)
        times = [f.time for f in scene.frames]
        self.assertEqual(times, sorted(times))

    def test_sample_scene_first_frame_has_all_types(self):
        """First frame has direct_speakers, LFE, audio_objects, and metadata nodes."""
        scene = parse_file(SAMPLE_SCENE)
        first = scene.frames[0]
        self.assertEqual(len(first.get_nodes_by_type("direct_speaker")), 3)
        self.assertEqual(len(first.get_nodes_by_type("LFE")), 1)
        self.assertEqual(len(first.get_nodes_by_type("audio_object")), 2)
        self.assertEqual(len(first.get_nodes_by_type("spectral_features")), 1)
        self.assertEqual(len(first.get_nodes_by_type("agent_state")), 1)

    def test_sample_scene_last_frame_stripped(self):
        """Last frame in fixture has only audio_object nodes — should still parse."""
        scene = parse_file(SAMPLE_SCENE)
        last = scene.frames[-1]
        self.assertEqual(len(last.get_nodes_by_type("audio_object")), 2)
        self.assertEqual(len(last.get_nodes_by_type("spectral_features")), 0)
        self.assertEqual(len(last.get_nodes_by_type("agent_state")), 0)
        self.assertEqual(len(last.get_nodes_by_type("direct_speaker")), 0)


if __name__ == "__main__":
    unittest.main()
