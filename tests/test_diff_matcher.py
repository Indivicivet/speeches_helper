import unittest
from src.core.diff_matcher import FuzzyDiffMatcher


class TestFuzzyDiffMatcher(unittest.TestCase):
    def setUp(self):
        self.matcher = FuzzyDiffMatcher(
            similar_threshold=0.65, different_threshold=0.35
        )

    def test_text_similarity(self):
        # Exact match
        sim_exact = self.matcher.calculate_text_similarity(
            "Welcome to the conference", "Welcome to the conference"
        )
        self.assertEqual(sim_exact, 1.0)

        # High similarity (minor word addition)
        sim_high = self.matcher.calculate_text_similarity(
            "Welcome to our annual conference", "Welcome to the annual conference"
        )
        self.assertGreaterEqual(sim_high, 0.70)

        # Completely different
        sim_low = self.matcher.calculate_text_similarity(
            "Now I would like to show some graphs",
            "Let's order some pizza for lunch",
        )
        self.assertLessEqual(sim_low, 0.35)

    def test_compare_sessions(self):
        session_a = {
            "session_id": "session_A",
            "profile": {
                "effective_duration_seconds": 120.0,
                "total_words": 200,
                "speaking_pace_wpm": 100.0,
                "pauses_count": 4,
                "timeline_items": [
                    {
                        "type": "speech",
                        "start": 0.0,
                        "end": 10.0,
                        "duration": 10.0,
                        "wpm": 120.0,
                        "text": "Good morning everybody welcome to my presentation.",
                    }
                ],
            },
        }

        session_b = {
            "session_id": "session_B",
            "profile": {
                "effective_duration_seconds": 130.0,
                "total_words": 210,
                "speaking_pace_wpm": 97.0,
                "pauses_count": 6,
                "timeline_items": [
                    {
                        "type": "speech",
                        "start": 0.0,
                        "end": 10.5,
                        "duration": 10.5,
                        "wpm": 115.0,
                        "text": "Good morning everyone and welcome to my presentation.",
                    }
                ],
            },
        }

        result = self.matcher.compare_sessions(session_a, session_b)
        metrics = result["metrics"]
        self.assertEqual(metrics["duration_delta"], 10.0)
        self.assertEqual(metrics["words_delta"], 10)
        self.assertEqual(metrics["pauses_delta"], 2)

        aligned_pairs = result["aligned_pairs"]
        self.assertEqual(len(aligned_pairs), 1)
        self.assertEqual(aligned_pairs[0]["status"], "similar")


if __name__ == "__main__":
    unittest.main()
