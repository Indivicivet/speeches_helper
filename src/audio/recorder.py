import io
import os
import subprocess
import wave
from pathlib import Path
import numpy as np
from PySide6.QtCore import QObject, Signal

try:
    import sounddevice as sd
except ImportError:
    sd = None


class AudioRecorder(QObject):
    """Records microphone audio in background and encodes to MP3."""

    level_changed = Signal(float)  # 0.0 to 1.0 for audio level indicator
    initial_audio_missing = Signal()  # Emitted if first 5s of recording have no audio

    def __init__(self, sample_rate=16000, channels=1, gain_db=10.0):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.gain_db = float(gain_db)
        self.is_recording = False
        self._stream = None
        self._chunks = []
        self._first_5s_peak = 0.0
        self._first_5s_sum_sq = 0.0
        self._first_5s_samples = 0
        self._first_5s_checked = False

    def set_gain_db(self, gain_db):
        """Set software recording gain in dB."""
        self.gain_db = float(gain_db)

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_recording:
            return

        # Apply software gain in dB (+10 dB default = ~3.16x amplitude)
        if self.gain_db != 0.0:
            multiplier = 10.0 ** (self.gain_db / 20.0)
            boosted = np.clip(
                indata.astype(np.float32) * multiplier, -32768, 32767
            ).astype(np.int16)
        else:
            boosted = indata.copy()

        self._chunks.append(boosted)

        if not self._first_5s_checked:
            needed = max(
                0, min(frames, int(5.0 * self.sample_rate) - self._first_5s_samples)
            )
            if needed > 0:
                sub = boosted[:needed]
                self._first_5s_peak = max(
                    self._first_5s_peak, float(np.max(np.abs(sub)))
                )
                self._first_5s_sum_sq += float(np.sum(sub.astype(np.float64) ** 2))
                self._first_5s_samples += needed

            if self._first_5s_samples >= int(5.0 * self.sample_rate):
                self._first_5s_checked = True
                if not self.has_initial_audio():
                    self.initial_audio_missing.emit()

        # Calculate approximate RMS volume level for UI feedback (0.0 to 1.0)
        rms = (
            float(np.sqrt(np.mean(boosted.astype(np.float32) ** 2)))
            if len(boosted) > 0
            else 0.0
        )
        self.level_changed.emit(min(1.0, (rms / 32767.0) * 12.0))

    def has_initial_audio(self):
        """Returns True if the recording had detectable audio in the first 5 seconds."""
        if not self._chunks and self._first_5s_samples == 0:
            return False
        total = self._first_5s_samples
        if total <= 0:
            return False
        rms = np.sqrt(self._first_5s_sum_sq / total)
        return not (rms < (0.001 * 32767) and self._first_5s_peak < (0.015 * 32767))

    def start(self):
        """Starts recording audio from default input device."""
        if sd is None:
            raise RuntimeError(
                "sounddevice is not installed. Please install sounddevice."
            )
        self._chunks = []
        self._first_5s_peak = 0.0
        self._first_5s_sum_sq = 0.0
        self._first_5s_samples = 0
        self._first_5s_checked = False
        self.is_recording = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self, output_mp3_path):
        """Stops recording and saves to output_mp3_path."""
        self.is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._first_5s_checked and self._first_5s_samples > 0:
            self._first_5s_checked = True
            if not self.has_initial_audio():
                self.initial_audio_missing.emit()

        if not self._chunks:
            # Create a 0.5s silent file to prevent empty file crashes
            empty_pcm = np.zeros(int(self.sample_rate * 0.5), dtype=np.int16).tobytes()
            self._encode_pcm_to_mp3(empty_pcm, output_mp3_path)
            return output_mp3_path

        audio_array = np.concatenate(self._chunks, axis=0)
        pcm_bytes = audio_array.tobytes()
        self._encode_pcm_to_mp3(pcm_bytes, output_mp3_path)
        return output_mp3_path

    def _encode_pcm_to_mp3(self, pcm_bytes, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Try lameenc (fastest, cleanest in-process MP3 encoding)
        try:
            import lameenc

            encoder = lameenc.Encoder()
            encoder.set_bit_rate(128)
            encoder.set_in_sample_rate(self.sample_rate)
            encoder.set_channels(self.channels)
            encoder.set_quality(2)
            mp3_data = encoder.encode(pcm_bytes)
            mp3_data += encoder.flush()
            with open(output_path, "wb") as f:
                f.write(mp3_data)
            return
        except ImportError:
            pass

        # 2. Try ffmpeg CLI if available
        try:
            process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "s16le",
                    "-ar",
                    str(self.sample_rate),
                    "-ac",
                    str(self.channels),
                    "-i",
                    "pipe:0",
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    str(output_path),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            process.communicate(input=pcm_bytes)
            if process.returncode == 0 and output_path.exists():
                return
        except Exception:
            pass

        # 3. Fallback: write standard WAV if MP3 encoder is unavailable
        wav_fallback = output_path.with_suffix(".wav")
        with wave.open(str(wav_fallback), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_bytes)

        # Rename or copy to output_path so file path expectations are satisfied
        if not output_path.exists():
            import shutil

            shutil.copyfile(wav_fallback, output_path)


def check_audio_file_initial_energy(
    audio_path, duration_seconds=5.0, rms_threshold=0.001, peak_threshold=0.015
):
    """Checks whether the first duration_seconds of an audio file contains detectable sound.

    Returns True if audio energy exceeds thresholds, False if silent or unreadable.
    """
    path = Path(audio_path)
    if not path.exists():
        return False
    try:
        from faster_whisper.audio import decode_audio

        audio = decode_audio(str(path), sampling_rate=16000)
        samples = audio[: int(duration_seconds * 16000)]
        if len(samples) == 0:
            return False
        rms = float(np.sqrt(np.mean(samples**2)))
        peak = float(np.max(np.abs(samples)))
        return rms > rms_threshold or peak > peak_threshold
    except Exception:
        return True
