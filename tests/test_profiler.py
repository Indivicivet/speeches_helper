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

    def test_phone_timer_events_in_timeline(self):
        segments = [
            {"start": 1.0, "end": 4.0, "text": "Starting my speech."},
            {"start": 7.0, "end": 10.0, "text": "Concluding my speech."},
        ]
        phone_data = {
            "starts": [
                {"start_time_seconds": 2.0, "duration_seconds": 5.0}  # alarm at 7.0s
            ]
        }
        result = self.profiler.analyze(
            segments=segments,
            global_duration_seconds=12.0,
            phone_timer_data=phone_data,
        )

        types = [item["type"] for item in result["timeline_items"]]
        self.assertIn("phone_timer_start", types)
        self.assertIn("phone_timer_alarm", types)

        # Chronological order verification
        starts = [item["start"] for item in result["timeline_items"]]
        self.assertEqual(starts, sorted(starts))

    def test_phone_timer_splits_speech_block_inline(self):
        segments = [
            {
                "start": 1.0,
                "end": 6.0,
                "text": "I was talking and then timer",
                "words": [
                    {"word": "I", "start": 1.0, "end": 1.4},
                    {"word": "was", "start": 1.5, "end": 2.0},
                    {"word": "talking", "start": 2.1, "end": 3.0},
                    {"word": "and", "start": 4.0, "end": 4.4},
                    {"word": "then", "start": 4.5, "end": 5.0},
                    {"word": "timer", "start": 5.1, "end": 6.0},
                ],
            }
        ]
        phone_data = {
            "starts": [{"start_time_seconds": 3.5, "duration_seconds": 180.0}]
        }
        result = self.profiler.analyze(
            segments=segments,
            global_duration_seconds=10.0,
            phone_timer_data=phone_data,
        )

        items = result["timeline_items"]
        # Expected sequence: speech (I was talking) -> phone_timer_start -> speech (and then timer)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["type"], "speech")
        self.assertIn("talking", items[0]["text"])
        self.assertEqual(items[1]["type"], "phone_timer_start")
        self.assertEqual(items[1]["start"], 3.5)
        self.assertEqual(items[2]["type"], "speech")
        self.assertIn("timer", items[2]["text"])


if __name__ == "__main__":
    unittest.main()
