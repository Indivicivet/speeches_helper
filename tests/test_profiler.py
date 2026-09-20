import unittest
from src.core.profiler import SpeechProfiler


class TestSpeechProfiler(unittest.TestCase):
    def setUp(self):
        self.profiler = SpeechProfiler(pause_threshold_seconds=1.5)

    def test_empty_segments(self):
        result = self.profiler.analyze(segments=[], global_duration_seconds=10.0)
        self.assertEqual(result["total_words"], 0)
        self.assertEqual(result["effective_duration_seconds"], 10.0)
        self.assertEqual(result["pauses_count"], 0)

    def test_pauses_and_effective_duration(self):
        segments = [
            {"start": 2.0, "end": 6.0, "text": "Good evening ladies and gentlemen."},
            {
                "start": 8.5,
                "end": 12.0,
                "text": "Thank you very much for having me tonight.",
            },
        ]
        # Global duration 15.0s, last speech at 12.0s
        result = self.profiler.analyze(segments=segments, global_duration_seconds=15.0)

        # Intro pause: 0.0 to 2.0s is 2.0s >= 1.5s
        # Mid pause: 6.0 to 8.5s is 2.5s >= 1.5s
        self.assertEqual(result["pauses_count"], 2)
        self.assertEqual(result["total_words"], 13)
        self.assertEqual(result["last_speech_time_seconds"], 12.0)
        self.assertEqual(result["effective_duration_seconds"], 12.0)
        self.assertEqual(result["trailing_silence_seconds"], 3.0)

        # Check timeline items
        items = result["timeline_items"]
        self.assertEqual(len(items), 4)  # pause, speech, pause, speech
        self.assertEqual(items[0]["type"], "pause")
        self.assertEqual(items[1]["type"], "speech")
        self.assertEqual(items[2]["type"], "pause")
        self.assertEqual(items[3]["type"], "speech")


if __name__ == "__main__":
    unittest.main()
