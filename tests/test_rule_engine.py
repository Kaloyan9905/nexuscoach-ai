"""Unit tests for the Deterministic Rule Engine."""

import unittest
from tests.fixtures.sample_match import get_sample_match_data
from nexuscoach.engine.rule_engine import RuleEngine
from nexuscoach.llm.normalizer import normalize_coaching_context
from nexuscoach.llm.synthesizer import CoachingSynthesizer

class TestRuleEngine(unittest.TestCase):

    def setUp(self):
        self.match, self.timeline, self.puuid = get_sample_match_data()
        self.engine = RuleEngine(self.match, self.timeline, self.puuid)

    def test_run_analysis_identifies_top_anomalies(self):
        analysis = self.engine.run_analysis()
        self.assertNotIn("error", analysis)
        self.assertEqual(analysis["metadata"]["userChampion"], "Ahri")
        self.assertEqual(analysis["metadata"]["opponentChampion"], "Syndra")
        self.assertEqual(analysis["metadata"]["result"], "Defeat")

        anomalies = analysis["top_anomalies"]
        self.assertGreaterEqual(len(anomalies), 3)

        # Check that Death at 07:12 is detected
        death_events = [a for a in anomalies if a.get("type") == "DEATH_ANALYSIS"]
        self.assertTrue(len(death_events) >= 1)
        death = death_events[0]
        self.assertEqual(death["timestamp"], "07:12")
        self.assertEqual(death["engagement_type"], "1v2 Gank")
        self.assertFalse(death["had_vision"])
        self.assertTrue(death["flash_available"])
        self.assertEqual(death["plates_lost_after"], 1)

        # Check Gold Hoarding at ~11:00 is detected
        gold_events = [a for a in anomalies if a.get("type") == "GOLD_HOARDING"]
        self.assertTrue(len(gold_events) >= 1)
        gold = gold_events[0]
        self.assertEqual(gold["held_gold"], 1850)
        self.assertGreaterEqual(gold["duration_seconds"], 120)

        # Check Objective Desync at 19:30 is detected
        obj_events = [a for a in anomalies if a.get("type") == "OBJECTIVE_DESYNC"]
        self.assertTrue(len(obj_events) >= 1)
        obj = obj_events[0]
        self.assertEqual(obj["timestamp"], "19:30")
        self.assertEqual(obj["objective"], "DRAGON")
        self.assertTrue(obj["lost_to_enemy"])

    def test_normalizer_generates_valid_json(self):
        analysis = self.engine.run_analysis()
        manifest_str = normalize_coaching_context(analysis)
        self.assertTrue(len(manifest_str) > 100)
        self.assertIn("Ahri", manifest_str)
        self.assertIn("Syndra", manifest_str)

    def test_offline_synthesizer_generates_3_takeaways(self):
        analysis = self.engine.run_analysis()
        synthesizer = CoachingSynthesizer()
        review = synthesizer.generate_review(analysis)
        self.assertIn("NexusCoach Review: Ahri vs Syndra", review)
        self.assertIn("07:12", review)
        self.assertIn("19:30", review)

if __name__ == "__main__":
    unittest.main()
