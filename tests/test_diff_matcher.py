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

    def test_align_segments_with_inserted_tangent_resync(self):
        items_a = [
            {"text": "Welcome everyone to our annual presentation."},
            {"text": "Today we discuss our quarterly financial results."},
            {"text": "Thank you all for your time and attention."},
        ]
        # Speech B has an inserted tangent at position 1
        items_b = [
            {"text": "Welcome everyone to our annual presentation."},
            {"text": "Before starting, here is a quick funny story."},
            {"text": "Today we discuss our quarterly financial results."},
            {"text": "Thank you all for your time and attention."},
        ]

        pairs = self.matcher.align_segments(items_a, items_b)

        # Should produce 4 rows: 1 matched, 1 gap on A's side, 2 matched
        self.assertEqual(len(pairs), 4)

        # Row 0: matched welcome
        self.assertIsNotNone(pairs[0]["item_a"])
        self.assertIsNotNone(pairs[0]["item_b"])
        self.assertEqual(pairs[0]["status"], "similar")

        # Row 1: gap on A, inserted tangent on B
        self.assertIsNone(pairs[1]["item_a"])
        self.assertIsNotNone(pairs[1]["item_b"])
        self.assertEqual(pairs[1]["status"], "missing")
        self.assertIn("funny story", pairs[1]["item_b"]["text"])

        # Row 2: successfully resynced on financial results
        self.assertIsNotNone(pairs[2]["item_a"])
        self.assertIsNotNone(pairs[2]["item_b"])
        self.assertEqual(pairs[2]["status"], "similar")
        self.assertIn("financial results", pairs[2]["item_a"]["text"])

        # Row 3: successfully resynced on thank you
        self.assertIsNotNone(pairs[3]["item_a"])
        self.assertIsNotNone(pairs[3]["item_b"])
        self.assertEqual(pairs[3]["status"], "similar")


if __name__ == "__main__":
    unittest.main()
