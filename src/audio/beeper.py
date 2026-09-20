import math
import tempfile
import wave
from pathlib import Path
from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect


class PhoneBeeper(QObject):
    """Generates and plays a looping phone timer alarm chime."""

    def __init__(self, sample_rate=44100):
        super().__init__()
        self.sample_rate = sample_rate
        self.temp_wav_path = Path(tempfile.gettempdir()) / "phone_alarm_chime.wav"
        self._generate_chime_wav(self.temp_wav_path)

        self.sound_effect = QSoundEffect()
        self.sound_effect.setSource(QUrl.fromLocalFile(str(self.temp_wav_path)))
        self.sound_effect.setLoopCount(QSoundEffect.Loop.Infinite.value)
        self.sound_effect.setVolume(0.85)

    def _generate_chime_wav(self, output_path):
        """Synthesizes a clean two-tone phone alarm pattern."""
        duration = 1.0  # 1 second total repeating loop
        num_samples = int(self.sample_rate * duration)
        raw_samples = []

        freq1, freq2 = 880.0, 1174.66  # A5 and D6 musical chime

        for i in range(num_samples):
            t = float(i) / self.sample_rate
            val = 0.0
            # Beep 1: 0.0s - 0.15s
            if 0.0 <= t < 0.15:
                envelope = math.sin(math.pi * (t / 0.15))
                val = 0.6 * envelope * math.sin(2.0 * math.pi * freq1 * t)
            # Beep 2: 0.20s - 0.35s
            elif 0.20 <= t < 0.35:
                envelope = math.sin(math.pi * ((t - 0.20) / 0.15))
                val = 0.7 * envelope * math.sin(2.0 * math.pi * freq2 * t)
            # Silence for the remainder of the 1 second

            sample_int = int(max(-1.0, min(1.0, val)) * 32767.0)
            raw_samples.append(sample_int)

        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            import struct

            wf.writeframes(struct.pack(f"<{len(raw_samples)}h", *raw_samples))

    def start_alarm(self):
        """Starts continuous looping alarm."""
        if not self.sound_effect.isPlaying():
            self.sound_effect.play()

    def stop_alarm(self):
        """Silences the alarm."""
        if self.sound_effect.isPlaying():
            self.sound_effect.stop()

    def is_alarming(self):
        return self.sound_effect.isPlaying()
