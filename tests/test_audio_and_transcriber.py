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


if __name__ == "__main__":
    unittest.main()
