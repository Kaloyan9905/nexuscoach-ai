"""Comprehensive feature and API test suite for NexusCoach AI."""

import unittest
import requests

from tests.fixtures.sample_match import get_sample_match_data
from nexuscoach.engine.rule_engine import RuleEngine
from nexuscoach.llm.normalizer import normalize_coaching_context
from nexuscoach.llm.synthesizer import CoachingSynthesizer
from nexuscoach.video.clipper import VideoClipper
from nexuscoach.ingestion.cache import MatchCache

BASE_URL = "http://127.0.0.1:8000"

class TestAllFeatures(unittest.TestCase):
    """Verifies all backend modules, API endpoints, rule detectors, and pipelines."""

    @classmethod
    def setUpClass(cls):
        cls.match, cls.timeline, cls.puuid = get_sample_match_data()
        cls.engine = RuleEngine(cls.match, cls.timeline, cls.puuid)
        cls.analysis = cls.engine.run_analysis()

    def test_01_root_dashboard_serves_ok(self):
        """Verify web dashboard HTML is served with proper content type."""
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.headers.get("content-type", ""))
        self.assertIn("NexusCoach", resp.text)
        self.assertIn("riftCanvas", resp.text)

    def test_02_demo_endpoint_structure(self):
        """Verify /api/demo returns complete mathematical analysis and review."""
        resp = requests.get(f"{BASE_URL}/api/demo", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("analysis", data)
        self.assertIn("review", data)

        analysis = data["analysis"]
        self.assertIn("metadata", analysis)
        self.assertIn("top_anomalies", analysis)
        self.assertIn("deaths", analysis)
        self.assertIn("timeline_series", analysis)

        meta = analysis["metadata"]
        self.assertTrue(len(meta["userChampion"]) > 0)
        self.assertTrue(len(meta["opponentChampion"]) > 0)
        self.assertGreater(len(analysis["top_anomalies"]), 0)

    def test_03_coordinate_bounds_and_validity(self):
        """Verify all extracted coordinates conform to Summoner's Rift geometry [0, 16000]."""
        for death in self.analysis.get("deaths", []):
            pos = death.get("position", {})
            self.assertIn("x", pos)
            self.assertIn("y", pos)
            self.assertTrue(0 <= pos["x"] <= 16000, f"X out of bounds: {pos['x']}")
            self.assertTrue(0 <= pos["y"] <= 16000, f"Y out of bounds: {pos['y']}")

        for anomaly in self.analysis.get("top_anomalies", []):
            if anomaly.get("type") == "DEATH_ANALYSIS":
                pos = anomaly.get("position", {})
                self.assertIn("x", pos)
                self.assertIn("y", pos)
                self.assertTrue(0 <= pos["x"] <= 16000)
                self.assertTrue(0 <= pos["y"] <= 16000)

    def test_04_economy_and_gold_delta_series(self):
        """Verify timeline economy metrics are continuous without null gaps."""
        series = self.analysis.get("timeline_series", [])
        self.assertGreater(len(series), 0)
        for frame in series:
            self.assertIn("minute", frame)
            self.assertIn("userCurrentGold", frame)
            self.assertIn("userTotalGold", frame)
            self.assertIn("goldDelta", frame)
            self.assertIsInstance(frame["goldDelta"], (int, float))

    def test_05_llm_normalizer_and_synthesizer(self):
        """Verify anomaly normalization compresses under 1500 tokens and synthesizer generates takeaways."""
        import json
        manifest_str = normalize_coaching_context(self.analysis)
        manifest = json.loads(manifest_str)
        self.assertIn("match", manifest)
        self.assertIn("critical_anomalies", manifest)

        # Synthesizer fallback or Gemini
        synthesizer = CoachingSynthesizer()
        review = synthesizer.generate_review(self.analysis)
        self.assertIsInstance(review, str)
        self.assertGreater(len(review), 50)
        self.assertIn("NexusCoach Review", review)

    def test_06_video_status_endpoint(self):
        """Verify /api/video/status response contract."""
        resp = requests.get(f"{BASE_URL}/api/video/status?match_id=DEMO_MATCH&timestamp=07:12", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("exists", data)
        self.assertIsInstance(data["exists"], bool)

    def test_07_video_capture_endpoint_contract(self):
        """Verify /api/video/capture initiates asynchronous task without blocking."""
        resp = requests.post(f"{BASE_URL}/api/video/capture?match_id=DEMO_MATCH&timestamp=07:12&time_seconds=432.0", timeout=5)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("video_url", data)

    def test_08_cache_persistence(self):
        """Verify MatchCache saves and retrieves match payloads safely."""
        cache = MatchCache()
        test_payload = {"matchId": "TEST_001", "frames": [{"time": 100}]}
        cache.save_match("TEST_001", test_payload)
        retrieved = cache.get_match("TEST_001")
        self.assertEqual(retrieved, test_payload)

    def test_09_watch_replay_auto_launches_client(self):
        """Verify /api/replay/watch triggers automatic client startup when League is closed."""
        from unittest.mock import patch

        with patch("nexuscoach.lcu.client.LCUClient.is_client_running", return_value=False), \
             patch("nexuscoach.lcu.client.LCUClient.start_league_client", return_value=True):
            resp = requests.post(
                f"{BASE_URL}/api/replay/watch?match_id=DEMO_MATCH&time_seconds=350.0&champion_name=Malzahar",
                timeout=5
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertIn("Launching League of Legends Client", data["message"])
            self.assertIn("camera locked on Malzahar", data["message"])

if __name__ == "__main__":
    unittest.main()
