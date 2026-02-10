# ARCHIVED: Tests for old xmlParser.py. New tests in test_xml_etree_parser.py. See LUSID/internalDocs/AGENTS.md#archival-plan

"""
Tests for LUSID Scene v0.5 — xmlParser (ADM dicts → LUSID scene)
stdlib only — no external dependencies
"""

import json
import os
import sys
import tempfile
import unittest
import warnings
from collections import OrderedDict
from pathlib import Path

# Allow imports from LUSID/src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.xmlParser import (
    _DEV_LFE_HARDCODED,
    _build_channel_audio_map,
    _is_lfe_channel,
    _parse_timecode_to_seconds,
    adm_to_lusid_scene,
    write_lusid_scene,
)
from src.scene import (
    AudioObjectNode,
    DirectSpeakerNode,
    LFENode,
    LusidScene,
)


# ---------------------------------------------------------------------------
# Helpers — mock ADM dicts
# ---------------------------------------------------------------------------

def make_direct_speaker_data(count=3, lfe_at=None):
    """Build a minimal directSpeakerData dict with `count` speakers.

    Keys are ordered: RC_L, RC_R, RC_C, RC_LFE (if lfe_at set), ...
    `lfe_at` is the 1-based position to place LFE (default: None = no LFE).
    """
    labels = ["RC_L", "RC_R", "RC_C", "RC_Ls", "RC_Rs", "RC_TL", "RC_TR",
              "RC_TBL", "RC_TBR", "RC_Cs"]
    data = OrderedDict()
    j = 0
    for i in range(1, count + 1):
        if lfe_at is not None and i == lfe_at:
            data[f"Speaker_{i}_LFE"] = {
                "x": 0.0, "y": -1.0, "z": 0.0,
                "speakerLabel": "LFE",
                "channelID": f"AC_{i:08d}",
            }
        else:
            label = labels[j] if j < len(labels) else f"RC_{i}"
            data[f"Speaker_{i}"] = {
                "x": float(i * 0.1),
                "y": 1.0,
                "z": 0.0,
                "speakerLabel": label,
                "channelID": f"AC_{i:08d}",
            }
            j += 1
    return data


def make_object_data(count=2, blocks_per_obj=3):
    """Build a minimal objectData dict with `count` objects, each having `blocks_per_obj` position blocks."""
    data = OrderedDict()
    for i in range(1, count + 1):
        blocks = []
        for b in range(blocks_per_obj):
            t = b * 0.5
            blocks.append({
                "rtime": f"00:00:{t:08.5f}",
                "duration": "00:00:00.50000",
                "x": round(0.1 * i * (b + 1), 4),
                "y": round(1.0 - 0.1 * b, 4),
                "z": 0.0,
            })
        data[f"Object_{i}"] = blocks
    return data


def make_global_data(sample_rate=48000, duration="00:01:00.00000"):
    return {"SampleRate": str(sample_rate), "Duration": duration, "Format": "ADM BWF"}


def make_contains_audio(num_channels, silent_channels=None):
    """Build a containsAudio dict. `silent_channels` is a set of 0-based indices that are silent."""
    if silent_channels is None:
        silent_channels = set()
    channels = []
    for i in range(num_channels):
        channels.append({
            "channel_index": i,
            "contains_audio": i not in silent_channels,
        })
    return {"channels": channels}


# ---------------------------------------------------------------------------
# Timecode parsing
# ---------------------------------------------------------------------------

class TestTimecodeParser(unittest.TestCase):
    def test_simple_timecode(self):
        self.assertAlmostEqual(_parse_timecode_to_seconds("00:00:01.50000"), 1.5)

    def test_hours_minutes(self):
        self.assertAlmostEqual(_parse_timecode_to_seconds("01:02:03.50000"), 3723.5)

    def test_zero(self):
        self.assertEqual(_parse_timecode_to_seconds("00:00:00.00000"), 0.0)

    def test_bad_timecode_warns(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _parse_timecode_to_seconds("bad_timecode")
            self.assertTrue(any("Cannot parse" in str(x.message) for x in w))
        self.assertEqual(result, 0.0)


# ---------------------------------------------------------------------------
# Channel audio map
# ---------------------------------------------------------------------------

class TestBuildChannelAudioMap(unittest.TestCase):
    def test_basic_map(self):
        ca = make_contains_audio(5, silent_channels={2})
        m = _build_channel_audio_map(ca)
        self.assertTrue(m[0])
        self.assertTrue(m[1])
        self.assertFalse(m[2])
        self.assertTrue(m[3])
        self.assertTrue(m[4])

    def test_empty_input(self):
        m = _build_channel_audio_map({})
        self.assertEqual(m, {})

    def test_no_channels_key(self):
        m = _build_channel_audio_map({"something": "else"})
        self.assertEqual(m, {})


# ---------------------------------------------------------------------------
# LFE detection
# ---------------------------------------------------------------------------

class TestLFEDetection(unittest.TestCase):
    def test_hardcoded_channel_4(self):
        """With _DEV_LFE_HARDCODED=True, channel 4 is always LFE."""
        if not _DEV_LFE_HARDCODED:
            self.skipTest("_DEV_LFE_HARDCODED is False")
        self.assertTrue(_is_lfe_channel("anything", {}, 4))
        self.assertFalse(_is_lfe_channel("anything", {}, 3))
        self.assertFalse(_is_lfe_channel("anything", {}, 5))


# ---------------------------------------------------------------------------
# Core: adm_to_lusid_scene
# ---------------------------------------------------------------------------

class TestAdmToLusidBasic(unittest.TestCase):
    """Basic scene construction tests."""

    def test_empty_input(self):
        scene = adm_to_lusid_scene({}, {})
        self.assertIsInstance(scene, LusidScene)
        self.assertEqual(scene.version, "0.5")
        self.assertEqual(scene.frame_count, 0)

    def test_direct_speakers_only(self):
        ds = make_direct_speaker_data(count=3)
        scene = adm_to_lusid_scene({}, ds)
        self.assertEqual(scene.frame_count, 1)  # Single frame at t=0
        self.assertEqual(scene.frames[0].time, 0.0)
        self.assertEqual(scene.direct_speaker_groups(), [1, 2, 3])
        self.assertFalse(scene.has_lfe())

    def test_objects_only(self):
        obj = make_object_data(count=2, blocks_per_obj=3)
        scene = adm_to_lusid_scene(obj, {})
        self.assertEqual(scene.audio_object_groups(), [1, 2])
        self.assertEqual(scene.direct_speaker_groups(), [])
        # 3 time points: 0.0, 0.5, 1.0
        self.assertGreaterEqual(scene.frame_count, 3)


class TestAdmToLusidWithLFE(unittest.TestCase):
    """Test LFE detection and node creation."""

    def test_lfe_at_channel_4(self):
        """4 speakers with LFE at position 4 (hardcoded)."""
        ds = make_direct_speaker_data(count=4, lfe_at=4)
        scene = adm_to_lusid_scene({}, ds)

        frame0 = scene.frames[0]
        lfe_nodes = frame0.get_nodes_by_type("LFE")
        self.assertEqual(len(lfe_nodes), 1)
        self.assertEqual(lfe_nodes[0].id, "4.1")
        self.assertTrue(scene.has_lfe())

        # DirectSpeakers should be groups 1, 2, 3 (LFE at 4 is not a DirectSpeaker)
        self.assertEqual(scene.direct_speaker_groups(), [1, 2, 3])

    def test_lfe_not_at_channel_4(self):
        """If LFE label is at channel 2 but hardcoded expects 4, it's a DirectSpeaker."""
        if not _DEV_LFE_HARDCODED:
            self.skipTest("Testing hardcoded LFE behavior only")
        ds = make_direct_speaker_data(count=4, lfe_at=2)
        scene = adm_to_lusid_scene({}, ds)
        # LFE at position 2 is NOT detected by hardcoded method (channel 4)
        # Instead, channel 4 is normal speaker, detected as LFE
        lfe_nodes = scene.frames[0].get_nodes_by_type("LFE")
        # With hardcoded: channel 4 = LFE (always), channel 2 = NOT LFE
        self.assertEqual(len(lfe_nodes), 1)
        self.assertEqual(lfe_nodes[0].id, "4.1")


class TestAdmToLusidMixed(unittest.TestCase):
    """Test scenes with both DirectSpeakers and AudioObjects."""

    def test_mixed_scene_group_numbering(self):
        """DirectSpeakers get groups 1-N, objects get N+1+."""
        ds = make_direct_speaker_data(count=3)
        obj = make_object_data(count=2, blocks_per_obj=2)
        scene = adm_to_lusid_scene(obj, ds)

        self.assertEqual(scene.direct_speaker_groups(), [1, 2, 3])
        self.assertEqual(scene.audio_object_groups(), [4, 5])
        self.assertFalse(scene.has_lfe())

    def test_mixed_with_lfe(self):
        """3 speakers + LFE at 4 + 2 objects = groups 1,2,3(ds), 4(LFE), 5,6(obj)."""
        ds = make_direct_speaker_data(count=4, lfe_at=4)
        obj = make_object_data(count=2, blocks_per_obj=2)
        scene = adm_to_lusid_scene(obj, ds)

        self.assertEqual(scene.direct_speaker_groups(), [1, 2, 3])
        self.assertTrue(scene.has_lfe())
        self.assertEqual(scene.audio_object_groups(), [5, 6])

    def test_static_nodes_at_t0(self):
        """DirectSpeakers and LFE appear only in the t=0 frame."""
        ds = make_direct_speaker_data(count=2)
        obj = make_object_data(count=1, blocks_per_obj=3)
        scene = adm_to_lusid_scene(obj, ds)

        frame0 = scene.frames[0]
        self.assertEqual(frame0.time, 0.0)
        ds_nodes = frame0.get_nodes_by_type("direct_speaker")
        self.assertEqual(len(ds_nodes), 2)

        # Later frames should NOT have direct_speaker nodes
        for frame in scene.frames[1:]:
            self.assertEqual(len(frame.get_nodes_by_type("direct_speaker")), 0)


class TestAdmToLusidSilentChannels(unittest.TestCase):
    """Test that silent channels are skipped."""

    def test_silent_direct_speaker_skipped(self):
        """A silent DirectSpeaker channel should not appear in the scene."""
        ds = make_direct_speaker_data(count=3)
        ca = make_contains_audio(3, silent_channels={1})  # Channel 2 (0-indexed: 1) is silent
        scene = adm_to_lusid_scene({}, ds, contains_audio=ca)

        # Only 2 direct speakers should be present (channel 2 skipped)
        frame0 = scene.frames[0]
        ds_nodes = frame0.get_nodes_by_type("direct_speaker")
        self.assertEqual(len(ds_nodes), 2)

    def test_silent_object_skipped(self):
        """A silent AudioObject should not appear in the scene."""
        ds = make_direct_speaker_data(count=3)
        obj = make_object_data(count=2, blocks_per_obj=2)
        # Channels: 0,1,2 = speakers; 3,4 = objects
        ca = make_contains_audio(5, silent_channels={3})  # First object silent
        scene = adm_to_lusid_scene(obj, ds, contains_audio=ca)

        # Only 1 audio object group should be present
        self.assertEqual(len(scene.audio_object_groups()), 1)

    def test_no_audio_data_defaults_to_all_active(self):
        """When contains_audio is None/empty, all channels assumed active."""
        ds = make_direct_speaker_data(count=3)
        scene = adm_to_lusid_scene({}, ds, contains_audio=None)
        self.assertEqual(scene.direct_speaker_groups(), [1, 2, 3])

        scene2 = adm_to_lusid_scene({}, ds, contains_audio={})
        self.assertEqual(scene2.direct_speaker_groups(), [1, 2, 3])


class TestAdmToLusidMetadata(unittest.TestCase):
    """Test metadata propagation."""

    def test_global_data_to_metadata(self):
        gd = make_global_data(sample_rate=44100, duration="00:02:30.00000")
        ds = make_direct_speaker_data(count=1)
        scene = adm_to_lusid_scene({}, ds, global_data=gd)

        self.assertEqual(scene.sample_rate, 44100)
        self.assertEqual(scene.metadata["sourceFormat"], "ADM")
        self.assertEqual(scene.metadata["duration"], "00:02:30.00000")
        self.assertEqual(scene.metadata["format"], "ADM BWF")

    def test_default_sample_rate(self):
        scene = adm_to_lusid_scene({}, make_direct_speaker_data(count=1))
        self.assertEqual(scene.sample_rate, 48000)

    def test_missing_global_data(self):
        scene = adm_to_lusid_scene({}, make_direct_speaker_data(count=1), global_data=None)
        self.assertEqual(scene.sample_rate, 48000)
        self.assertEqual(scene.metadata["sourceFormat"], "ADM")


class TestAdmToLusidFrameStructure(unittest.TestCase):
    """Test frame ordering and structure."""

    def test_frames_sorted_by_time(self):
        obj = make_object_data(count=1, blocks_per_obj=5)
        scene = adm_to_lusid_scene(obj, {})
        times = [f.time for f in scene.frames]
        self.assertEqual(times, sorted(times))

    def test_node_ids_use_group_hierarchy_format(self):
        """All node IDs should be X.Y format."""
        ds = make_direct_speaker_data(count=2)
        obj = make_object_data(count=1, blocks_per_obj=2)
        scene = adm_to_lusid_scene(obj, ds)

        import re
        pattern = re.compile(r"^\d+\.\d+$")
        for frame in scene.frames:
            for node in frame.nodes:
                self.assertRegex(node.id, pattern,
                                 f"Node ID '{node.id}' doesn't match X.Y format")

    def test_direct_speaker_cart_values(self):
        """DirectSpeaker positions should match input data."""
        ds = OrderedDict()
        ds["Left"] = {"x": -1.0, "y": 1.0, "z": 0.5, "speakerLabel": "L", "channelID": "AC_1"}
        scene = adm_to_lusid_scene({}, ds)

        frame0 = scene.frames[0]
        ds_nodes = frame0.get_nodes_by_type("direct_speaker")
        self.assertEqual(len(ds_nodes), 1)
        self.assertEqual(ds_nodes[0].cart, [-1.0, 1.0, 0.5])
        self.assertEqual(ds_nodes[0].speakerLabel, "L")
        self.assertEqual(ds_nodes[0].channelID, "AC_1")


# ---------------------------------------------------------------------------
# File I/O: write_lusid_scene
# ---------------------------------------------------------------------------

class TestWriteLusidScene(unittest.TestCase):
    def test_write_and_read_back(self):
        """Write a scene to JSON, read it back, verify structure."""
        ds = make_direct_speaker_data(count=2)
        obj = make_object_data(count=1, blocks_per_obj=2)
        scene = adm_to_lusid_scene(obj, ds)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "stage" / "scene.lusid.json"
            result = write_lusid_scene(scene, out_path)

            self.assertTrue(result.exists())
            with open(result) as f:
                data = json.load(f)
            self.assertEqual(data["version"], "0.5")
            self.assertIn("frames", data)
            self.assertGreater(len(data["frames"]), 0)

    def test_write_creates_directories(self):
        """write_lusid_scene should create parent dirs if needed."""
        scene = adm_to_lusid_scene({}, make_direct_speaker_data(count=1))
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_path = Path(tmpdir) / "a" / "b" / "c" / "scene.lusid.json"
            result = write_lusid_scene(scene, deep_path)
            self.assertTrue(result.exists())


# ---------------------------------------------------------------------------
# Round-trip: adm → scene → JSON → parse → scene
# ---------------------------------------------------------------------------

class TestRoundTrip(unittest.TestCase):
    def test_adm_to_json_to_scene(self):
        """Full round-trip: ADM dicts → LUSID scene → JSON → parse back."""
        from src.parser import parse_dict

        ds = make_direct_speaker_data(count=3, lfe_at=4)
        # Add the LFE speaker to get 4 speakers total
        ds_with_lfe = make_direct_speaker_data(count=4, lfe_at=4)
        obj = make_object_data(count=2, blocks_per_obj=3)
        gd = make_global_data(sample_rate=48000)

        scene1 = adm_to_lusid_scene(obj, ds_with_lfe, global_data=gd)
        json_data = scene1.to_dict()

        # Parse the dict back
        scene2 = parse_dict(json_data)

        self.assertEqual(scene2.version, scene1.version)
        self.assertEqual(scene2.sample_rate, scene1.sample_rate)
        self.assertEqual(scene2.frame_count, scene1.frame_count)
        self.assertEqual(scene2.audio_object_groups(), scene1.audio_object_groups())
        self.assertEqual(scene2.direct_speaker_groups(), scene1.direct_speaker_groups())
        self.assertEqual(scene2.has_lfe(), scene1.has_lfe())


if __name__ == "__main__":
    unittest.main()
