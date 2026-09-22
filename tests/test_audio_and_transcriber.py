import unittest
import numpy as np
from src.audio.recorder import AudioRecorder
from src.core.transcriber import TranscriberThread


class TestAudioAndTranscriber(unittest.TestCase):
    def test_recorder_gain_default_and_callback(self):
        rec = AudioRecorder(gain_db=10.0)
        self.assertEqual(rec.gain_db, 10.0)

        # Simulate incoming audio callback
        rec.is_recording = True
        test_chunk = np.array([[1000], [2000], [-3000]], dtype=np.int16)
        rec._audio_callback(test_chunk, 3, None, None)

        self.assertEqual(len(rec._chunks), 1)
        # +10 dB is 10^(10/20) ~ 3.162
        expected_first = int(1000 * (10.0**0.5))
        self.assertAlmostEqual(rec._chunks[0][0][0], expected_first, delta=2)

    def test_recorder_clipping_protection(self):
        rec = AudioRecorder(gain_db=20.0)  # 10x multiplier
        rec.is_recording = True
        loud_chunk = np.array([[20000], [-25000]], dtype=np.int16)
        rec._audio_callback(loud_chunk, 2, None, None)

        # Should be cleanly clipped to int16 max/min without overflow
        self.assertEqual(rec._chunks[0][0][0], 32767)
        self.assertEqual(rec._chunks[0][1][0], -32768)

    def test_transcriber_vad_threshold(self):
        thread = TranscriberThread("dummy.mp3", vad_threshold=0.30)
        self.assertEqual(thread.vad_threshold, 0.30)

    def test_recorder_initial_audio_detection(self):
        rec = AudioRecorder(sample_rate=16000, gain_db=0.0)
        rec.is_recording = True

        warnings_received = []
        rec.initial_audio_missing.connect(lambda: warnings_received.append(True))

        # Feed 5 seconds of near-zero silence
        silent_chunk = np.zeros((16000, 1), dtype=np.int16)
        for _ in range(5):
            rec._audio_callback(silent_chunk, 16000, None, None)

        self.assertFalse(rec.has_initial_audio())
        self.assertEqual(len(warnings_received), 1)

        # New recording with audio
        rec2 = AudioRecorder(sample_rate=16000, gain_db=0.0)
        rec2.is_recording = True
        warnings2 = []
        rec2.initial_audio_missing.connect(lambda: warnings2.append(True))

        audible_chunk = np.full((16000, 1), 2000, dtype=np.int16)
        for _ in range(5):
            rec2._audio_callback(audible_chunk, 16000, None, None)

        self.assertTrue(rec2.has_initial_audio())
        self.assertEqual(len(warnings2), 0)


if __name__ == "__main__":
    unittest.main()
