"""
Tests for LUSID Scene v0.5 — Transcoder
stdlib only — no external dependencies
"""

import json
import sys
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser import parse_file, parse_dict
from src.transcoder import transcode_to_sonopleth, extract_metadata_sidecar


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_SCENE = FIXTURE_DIR / "sample_scene_v0.5.json"


# ---------------------------------------------------------------------------
# Transcoder: LUSID → sonoPleth
# ---------------------------------------------------------------------------

class TestTranscoder(unittest.TestCase):
    def _load_sample(self):
        return parse_file(SAMPLE_SCENE)

    def test_output_structure(self):
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        self.assertIn("sampleRate", out)
        self.assertIn("timeUnit", out)
        self.assertIn("sources", out)
        self.assertEqual(out["timeUnit"], "seconds")

    def test_sample_rate_from_scene(self):
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        self.assertEqual(out["sampleRate"], 48000)

    def test_audio_sources_named_by_group(self):
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        self.assertIn("src_1", out["sources"])
        self.assertIn("src_2", out["sources"])

    def test_lfe_present(self):
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        self.assertIn("LFE", out["sources"])
        self.assertEqual(out["sources"]["LFE"], [{"time": 0.0}])

    def test_lfe_has_no_cart(self):
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        lfe_entry = out["sources"]["LFE"][0]
        self.assertNotIn("cart", lfe_entry)

    def test_keyframe_count(self):
        """Sample scene has 5 frames, both groups present in all 5."""
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        self.assertEqual(len(out["sources"]["src_1"]), 5)
        self.assertEqual(len(out["sources"]["src_2"]), 5)

    def test_keyframe_structure(self):
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        kf = out["sources"]["src_1"][0]
        self.assertIn("time", kf)
        self.assertIn("cart", kf)
        self.assertIsInstance(kf["cart"], list)
        self.assertEqual(len(kf["cart"]), 3)

    def test_keyframes_time_sorted(self):
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        for src_name, keyframes in out["sources"].items():
            if src_name == "LFE":
                continue
            times = [kf["time"] for kf in keyframes]
            self.assertEqual(times, sorted(times),
                             f"Keyframes for {src_name} not sorted")

    def test_no_spectral_in_output(self):
        """spectral_features and agent_state must NOT appear in renderInstructions."""
        scene = self._load_sample()
        out = transcode_to_sonopleth(scene)
        for src_name in out["sources"]:
            self.assertNotIn("spectral", src_name.lower())
            self.assertNotIn("agent", src_name.lower())

    def test_no_lfe_when_absent(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "audio_object", "cart": [0, 1, 0]}
            ]}]
        }
        scene = parse_dict(raw)
        out = transcode_to_sonopleth(scene)
        self.assertNotIn("LFE", out["sources"])

    def test_time_conversion_ms(self):
        """Verify millisecond times are converted to seconds in output."""
        raw = {
            "version": "0.5",
            "timeUnit": "ms",
            "frames": [
                {"time": 0.0, "nodes": [
                    {"id": "1.1", "type": "audio_object", "cart": [0, 1, 0]}
                ]},
                {"time": 1500.0, "nodes": [
                    {"id": "1.1", "type": "audio_object", "cart": [1, 0, 0]}
                ]},
            ]
        }
        scene = parse_dict(raw)
        out = transcode_to_sonopleth(scene)
        kfs = out["sources"]["src_1"]
        self.assertAlmostEqual(kfs[0]["time"], 0.0)
        self.assertAlmostEqual(kfs[1]["time"], 1.5)

    def test_time_conversion_samples(self):
        raw = {
            "version": "0.5",
            "timeUnit": "samples",
            "sampleRate": 48000,
            "frames": [
                {"time": 0, "nodes": [
                    {"id": "1.1", "type": "audio_object", "cart": [0, 1, 0]}
                ]},
                {"time": 48000, "nodes": [
                    {"id": "1.1", "type": "audio_object", "cart": [1, 0, 0]}
                ]},
            ]
        }
        scene = parse_dict(raw)
        out = transcode_to_sonopleth(scene)
        kfs = out["sources"]["src_1"]
        self.assertAlmostEqual(kfs[1]["time"], 1.0)


# ---------------------------------------------------------------------------
# Metadata sidecar
# ---------------------------------------------------------------------------

class TestMetadataSidecar(unittest.TestCase):
    def test_sidecar_structure(self):
        scene = parse_file(SAMPLE_SCENE)
        sidecar = extract_metadata_sidecar(scene)
        self.assertIn("version", sidecar)
        self.assertIn("timeUnit", sidecar)
        self.assertIn("groups", sidecar)

    def test_sidecar_has_spectral(self):
        scene = parse_file(SAMPLE_SCENE)
        sidecar = extract_metadata_sidecar(scene)
        self.assertIn("1", sidecar["groups"])
        self.assertIn("spectral_features", sidecar["groups"]["1"])
        # 4 frames have spectral data (last frame doesn't)
        self.assertEqual(len(sidecar["groups"]["1"]["spectral_features"]), 4)

    def test_sidecar_has_agent_state(self):
        scene = parse_file(SAMPLE_SCENE)
        sidecar = extract_metadata_sidecar(scene)
        self.assertIn("2", sidecar["groups"])
        self.assertIn("agent_state", sidecar["groups"]["2"])
        self.assertEqual(len(sidecar["groups"]["2"]["agent_state"]), 4)

    def test_sidecar_entries_have_time(self):
        scene = parse_file(SAMPLE_SCENE)
        sidecar = extract_metadata_sidecar(scene)
        for entry in sidecar["groups"]["1"]["spectral_features"]:
            self.assertIn("time", entry)
            self.assertIn("centroid", entry)

    def test_no_audio_objects_in_sidecar(self):
        scene = parse_file(SAMPLE_SCENE)
        sidecar = extract_metadata_sidecar(scene)
        for group_data in sidecar["groups"].values():
            self.assertNotIn("audio_object", group_data)

    def test_empty_sidecar(self):
        raw = {
            "version": "0.5",
            "frames": [{"time": 0.0, "nodes": [
                {"id": "1.1", "type": "audio_object", "cart": [0, 1, 0]}
            ]}]
        }
        scene = parse_dict(raw)
        sidecar = extract_metadata_sidecar(scene)
        self.assertEqual(sidecar["groups"], {})


if __name__ == "__main__":
    unittest.main()
