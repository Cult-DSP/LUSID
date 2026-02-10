"""
Tests for LUSID xml_etree_parser — stdlib ADM XML → LUSID scene parser.

Tests cover:
  - Global data extraction from <Technical> section
  - DirectSpeaker extraction from EBU ADM XML
  - Object position extraction from EBU ADM XML
  - LFE detection
  - End-to-end: XML → LusidScene
  - Silent channel skipping
  - Standalone EBU XML (no bwfmetaedit wrapper)
  - Round-trip: parse → write → re-parse
"""

import os
import sys
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.xml_etree_parser import (
    _DEV_LFE_HARDCODED,
    _ebu,
    _parse_timecode_to_seconds,
    extract_direct_speaker_data,
    extract_global_data,
    extract_object_positions,
    parse_adm_xml_to_lusid_scene,
    parse_and_write_lusid_scene,
)
from src.scene import (
    AudioObjectNode,
    DirectSpeakerNode,
    LFENode,
    LusidScene,
)

# ---------------------------------------------------------------------------
# Fixtures — minimal bwfmetaedit conformance-point XML
# ---------------------------------------------------------------------------

MINIMAL_ADM_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<conformance_point_document>
    <File name="test.wav">
        <Technical>
            <FileSize>12345</FileSize>
            <Format>Wave</Format>
            <Channels>14</Channels>
            <SampleRate>48000</SampleRate>
            <BitPerSample>24</BitPerSample>
            <Duration>00:01:30.00000</Duration>
        </Technical>
        <aXML>
<ebuCoreMain xmlns="urn:ebu:metadata-schema:ebuCore_2016">
    <coreMetadata>
        <format>
            <audioFormatExtended>
                <audioChannelFormat audioChannelFormatID="AC_00011001" typeLabel="0001" typeDefinition="DirectSpeakers" audioChannelFormatName="RoomCentricLeft">
                    <audioBlockFormat audioBlockFormatID="AB_00011001_00000001">
                        <speakerLabel>RC_L</speakerLabel>
                        <cartesian>1</cartesian>
                        <position coordinate="X">-1</position>
                        <position coordinate="Y">1</position>
                    </audioBlockFormat>
                </audioChannelFormat>
                <audioChannelFormat audioChannelFormatID="AC_00011002" typeLabel="0001" typeDefinition="DirectSpeakers" audioChannelFormatName="RoomCentricRight">
                    <audioBlockFormat audioBlockFormatID="AB_00011002_00000001">
                        <speakerLabel>RC_R</speakerLabel>
                        <cartesian>1</cartesian>
                        <position coordinate="X">1</position>
                        <position coordinate="Y">1</position>
                    </audioBlockFormat>
                </audioChannelFormat>
                <audioChannelFormat audioChannelFormatID="AC_00011003" typeLabel="0001" typeDefinition="DirectSpeakers" audioChannelFormatName="RoomCentricCenter">
                    <audioBlockFormat audioBlockFormatID="AB_00011003_00000001">
                        <speakerLabel>RC_C</speakerLabel>
                        <cartesian>1</cartesian>
                        <position coordinate="X">0</position>
                        <position coordinate="Y">1</position>
                    </audioBlockFormat>
                </audioChannelFormat>
                <audioChannelFormat audioChannelFormatID="AC_00011004" typeLabel="0001" typeDefinition="DirectSpeakers" audioChannelFormatName="RoomCentricLFE">
                    <audioBlockFormat audioBlockFormatID="AB_00011004_00000001">
                        <speakerLabel>RC_LFE</speakerLabel>
                        <cartesian>1</cartesian>
                        <position coordinate="X">-1</position>
                        <position coordinate="Y">1</position>
                        <position coordinate="Z">-1</position>
                    </audioBlockFormat>
                </audioChannelFormat>
                <audioChannelFormat audioChannelFormatID="AC_0003100b" typeLabel="0003" typeDefinition="Objects" audioChannelFormatName="guitar L">
                    <audioBlockFormat audioBlockFormatID="AB_0003100B_00000001" rtime="00:00:00.00000" duration="00:00:10.00000">
                        <cartesian>1</cartesian>
                        <position coordinate="X">-0.5</position>
                        <position coordinate="Y">1.0</position>
                        <position coordinate="Z">0.0</position>
                    </audioBlockFormat>
                    <audioBlockFormat audioBlockFormatID="AB_0003100B_00000002" rtime="00:00:10.00000" duration="00:00:10.00000">
                        <cartesian>1</cartesian>
                        <position coordinate="X">0.5</position>
                        <position coordinate="Y">0.8</position>
                        <position coordinate="Z">0.2</position>
                    </audioBlockFormat>
                </audioChannelFormat>
                <audioChannelFormat audioChannelFormatID="AC_0003100c" typeLabel="0003" typeDefinition="Objects" audioChannelFormatName="guitar R">
                    <audioBlockFormat audioBlockFormatID="AB_0003100C_00000001" rtime="00:00:00.00000" duration="00:00:20.00000">
                        <cartesian>1</cartesian>
                        <position coordinate="X">0.5</position>
                        <position coordinate="Y">1.0</position>
                        <position coordinate="Z">0.0</position>
                    </audioBlockFormat>
                </audioChannelFormat>
            </audioFormatExtended>
        </format>
    </coreMetadata>
</ebuCoreMain>
        </aXML>
    </File>
</conformance_point_document>
"""


STANDALONE_EBU_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<ebuCoreMain xmlns="urn:ebu:metadata-schema:ebuCore_2016">
    <coreMetadata>
        <format>
            <audioFormatExtended>
                <audioChannelFormat audioChannelFormatID="AC_00011001" typeLabel="0001" typeDefinition="DirectSpeakers" audioChannelFormatName="Left">
                    <audioBlockFormat audioBlockFormatID="AB_00011001_00000001">
                        <speakerLabel>RC_L</speakerLabel>
                        <cartesian>1</cartesian>
                        <position coordinate="X">-1</position>
                        <position coordinate="Y">1</position>
                    </audioBlockFormat>
                </audioChannelFormat>
                <audioChannelFormat audioChannelFormatID="AC_0003100b" typeLabel="0003" typeDefinition="Objects" audioChannelFormatName="Obj1">
                    <audioBlockFormat audioBlockFormatID="AB_0003100B_00000001" rtime="00:00:00.00000" duration="00:00:05.00000">
                        <cartesian>1</cartesian>
                        <position coordinate="X">0.0</position>
                        <position coordinate="Y">1.0</position>
                        <position coordinate="Z">0.5</position>
                    </audioBlockFormat>
                </audioChannelFormat>
            </audioFormatExtended>
        </format>
    </coreMetadata>
</ebuCoreMain>
"""


def _write_temp_xml(content):
    """Write XML string to a temp file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTimecodeParser(unittest.TestCase):
    def test_standard_timecode(self):
        self.assertAlmostEqual(_parse_timecode_to_seconds("00:01:30.50000"), 90.5)

    def test_zero(self):
        self.assertAlmostEqual(_parse_timecode_to_seconds("00:00:00.00000"), 0.0)

    def test_hours(self):
        self.assertAlmostEqual(_parse_timecode_to_seconds("01:00:00.00000"), 3600.0)

    def test_fractional_seconds(self):
        self.assertAlmostEqual(
            _parse_timecode_to_seconds("00:00:15.47569"), 15.47569, places=5
        )


class TestExtractGlobalData(unittest.TestCase):
    def setUp(self):
        self.xml_path = _write_temp_xml(MINIMAL_ADM_XML)

    def tearDown(self):
        os.unlink(self.xml_path)

    def test_extracts_sample_rate(self):
        import xml.etree.ElementTree as ET
        tree = ET.parse(self.xml_path)
        data = extract_global_data(tree)
        self.assertEqual(data["SampleRate"], "48000")

    def test_extracts_duration(self):
        import xml.etree.ElementTree as ET
        tree = ET.parse(self.xml_path)
        data = extract_global_data(tree)
        self.assertEqual(data["Duration"], "00:01:30.00000")

    def test_extracts_format(self):
        import xml.etree.ElementTree as ET
        tree = ET.parse(self.xml_path)
        data = extract_global_data(tree)
        self.assertEqual(data["Format"], "Wave")

    def test_extracts_channels(self):
        import xml.etree.ElementTree as ET
        tree = ET.parse(self.xml_path)
        data = extract_global_data(tree)
        self.assertEqual(data["Channels"], "14")


class TestExtractDirectSpeakerData(unittest.TestCase):
    def setUp(self):
        import xml.etree.ElementTree as ET
        self.xml_path = _write_temp_xml(MINIMAL_ADM_XML)
        tree = ET.parse(self.xml_path)
        from src.xml_etree_parser import _find_ebu_root
        self.ebu_root = _find_ebu_root(tree)

    def tearDown(self):
        os.unlink(self.xml_path)

    def test_finds_all_direct_speakers(self):
        data = extract_direct_speaker_data(self.ebu_root)
        self.assertEqual(len(data), 4)

    def test_speaker_names(self):
        data = extract_direct_speaker_data(self.ebu_root)
        names = list(data.keys())
        self.assertIn("RoomCentricLeft", names)
        self.assertIn("RoomCentricRight", names)
        self.assertIn("RoomCentricCenter", names)
        self.assertIn("RoomCentricLFE", names)

    def test_speaker_label(self):
        data = extract_direct_speaker_data(self.ebu_root)
        self.assertEqual(data["RoomCentricLeft"]["speakerLabel"], "RC_L")

    def test_speaker_position(self):
        data = extract_direct_speaker_data(self.ebu_root)
        left = data["RoomCentricLeft"]
        self.assertAlmostEqual(left["x"], -1.0)
        self.assertAlmostEqual(left["y"], 1.0)
        self.assertAlmostEqual(left["z"], 0.0)

    def test_lfe_position(self):
        data = extract_direct_speaker_data(self.ebu_root)
        lfe = data["RoomCentricLFE"]
        self.assertAlmostEqual(lfe["z"], -1.0)

    def test_channel_id(self):
        data = extract_direct_speaker_data(self.ebu_root)
        self.assertEqual(data["RoomCentricLeft"]["channelID"], "AC_00011001")

    def test_preserves_order(self):
        data = extract_direct_speaker_data(self.ebu_root)
        names = list(data.keys())
        self.assertEqual(names[0], "RoomCentricLeft")
        self.assertEqual(names[3], "RoomCentricLFE")


class TestExtractObjectPositions(unittest.TestCase):
    def setUp(self):
        import xml.etree.ElementTree as ET
        self.xml_path = _write_temp_xml(MINIMAL_ADM_XML)
        tree = ET.parse(self.xml_path)
        from src.xml_etree_parser import _find_ebu_root
        self.ebu_root = _find_ebu_root(tree)

    def tearDown(self):
        os.unlink(self.xml_path)

    def test_finds_all_objects(self):
        data = extract_object_positions(self.ebu_root)
        self.assertEqual(len(data), 2)

    def test_object_names(self):
        data = extract_object_positions(self.ebu_root)
        names = list(data.keys())
        self.assertIn("guitar L", names)
        self.assertIn("guitar R", names)

    def test_block_count(self):
        data = extract_object_positions(self.ebu_root)
        self.assertEqual(len(data["guitar L"]), 2)
        self.assertEqual(len(data["guitar R"]), 1)

    def test_block_position(self):
        data = extract_object_positions(self.ebu_root)
        block = data["guitar L"][0]
        self.assertAlmostEqual(block["x"], -0.5)
        self.assertAlmostEqual(block["y"], 1.0)
        self.assertAlmostEqual(block["z"], 0.0)

    def test_block_timecode(self):
        data = extract_object_positions(self.ebu_root)
        block = data["guitar L"][1]
        self.assertEqual(block["rtime"], "00:00:10.00000")

    def test_channel_id_in_blocks(self):
        data = extract_object_positions(self.ebu_root)
        block = data["guitar L"][0]
        self.assertEqual(block["channelID"], "AC_0003100b")


class TestEndToEnd(unittest.TestCase):
    """Full pipeline: XML → LusidScene."""

    def setUp(self):
        self.xml_path = _write_temp_xml(MINIMAL_ADM_XML)

    def tearDown(self):
        os.unlink(self.xml_path)

    def test_produces_scene(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        self.assertIsInstance(scene, LusidScene)

    def test_scene_version(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        self.assertEqual(scene.version, "0.5")

    def test_scene_sample_rate(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        self.assertEqual(scene.sample_rate, 48000)

    def test_scene_has_frames(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        self.assertGreater(scene.frame_count, 0)

    def test_direct_speakers_in_scene(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        ds_groups = scene.direct_speaker_groups()
        self.assertEqual(len(ds_groups), 3)

    def test_lfe_in_scene(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        self.assertTrue(scene.has_lfe())

    def test_audio_objects_in_scene(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        ao_groups = scene.audio_object_groups()
        self.assertEqual(len(ao_groups), 2)

    def test_node_ids_are_correct(self):
        """DirectSpeakers get groups 1-4, Objects get groups 5-6."""
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        frame0 = scene.frames[0]
        ids = {n.id for n in frame0.nodes}
        self.assertIn("1.1", ids)
        self.assertIn("2.1", ids)
        self.assertIn("3.1", ids)
        self.assertIn("4.1", ids)
        self.assertIn("5.1", ids)
        self.assertIn("6.1", ids)

    def test_lfe_node_type(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        frame0 = scene.frames[0]
        lfe_nodes = frame0.get_nodes_by_type("LFE")
        self.assertEqual(len(lfe_nodes), 1)
        self.assertEqual(lfe_nodes[0].id, "4.1")

    def test_second_frame_has_object_position(self):
        """guitar L has a second block at t=10s."""
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        frame10 = None
        for f in scene.frames:
            if abs(f.time - 10.0) < 0.001:
                frame10 = f
                break
        self.assertIsNotNone(frame10, "Expected a frame at t=10.0")
        ao_nodes = frame10.get_nodes_by_type("audio_object")
        self.assertEqual(len(ao_nodes), 1)
        self.assertEqual(ao_nodes[0].id, "5.1")
        self.assertAlmostEqual(ao_nodes[0].cart[0], 0.5)

    def test_metadata(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        self.assertEqual(scene.metadata["sourceFormat"], "ADM")
        self.assertEqual(scene.metadata["duration"], "00:01:30.00000")


class TestSilentChannelSkipping(unittest.TestCase):
    def setUp(self):
        self.xml_path = _write_temp_xml(MINIMAL_ADM_XML)

    def tearDown(self):
        os.unlink(self.xml_path)

    def test_skips_silent_direct_speaker(self):
        contains_audio = {
            "channels": [
                {"channel_index": 0, "contains_audio": False},
                {"channel_index": 1, "contains_audio": True},
                {"channel_index": 2, "contains_audio": True},
                {"channel_index": 3, "contains_audio": True},
                {"channel_index": 4, "contains_audio": True},
                {"channel_index": 5, "contains_audio": True},
            ]
        }
        scene = parse_adm_xml_to_lusid_scene(self.xml_path, contains_audio=contains_audio)
        ds_groups = scene.direct_speaker_groups()
        self.assertNotIn(1, ds_groups)
        self.assertIn(2, ds_groups)

    def test_skips_silent_object(self):
        contains_audio = {
            "channels": [
                {"channel_index": 0, "contains_audio": True},
                {"channel_index": 1, "contains_audio": True},
                {"channel_index": 2, "contains_audio": True},
                {"channel_index": 3, "contains_audio": True},
                {"channel_index": 4, "contains_audio": False},
                {"channel_index": 5, "contains_audio": True},
            ]
        }
        scene = parse_adm_xml_to_lusid_scene(self.xml_path, contains_audio=contains_audio)
        ao_groups = scene.audio_object_groups()
        self.assertNotIn(5, ao_groups)
        self.assertIn(6, ao_groups)


class TestStandaloneEbuXml(unittest.TestCase):
    def setUp(self):
        self.xml_path = _write_temp_xml(STANDALONE_EBU_XML)

    def tearDown(self):
        os.unlink(self.xml_path)

    def test_parses_standalone_ebu(self):
        scene = parse_adm_xml_to_lusid_scene(self.xml_path)
        self.assertIsInstance(scene, LusidScene)
        self.assertEqual(len(scene.direct_speaker_groups()), 1)
        self.assertEqual(len(scene.audio_object_groups()), 1)


class TestWriteAndReload(unittest.TestCase):
    def setUp(self):
        self.xml_path = _write_temp_xml(MINIMAL_ADM_XML)
        self.output_dir = tempfile.mkdtemp()
        self.output_path = os.path.join(self.output_dir, "scene.lusid.json")

    def tearDown(self):
        os.unlink(self.xml_path)
        if os.path.exists(self.output_path):
            os.unlink(self.output_path)
        os.rmdir(self.output_dir)

    def test_write_and_reload(self):
        scene = parse_and_write_lusid_scene(self.xml_path, self.output_path)
        self.assertTrue(os.path.exists(self.output_path))

        from src.parser import parse_file
        reloaded = parse_file(self.output_path)
        self.assertEqual(reloaded.version, scene.version)
        self.assertEqual(reloaded.frame_count, scene.frame_count)
        self.assertEqual(reloaded.sample_rate, scene.sample_rate)


if __name__ == "__main__":
    unittest.main()
