from PySide6.QtCore import QThread, Signal

_MODEL_CACHE = {}


class TranscriberThread(QThread):
    """Background worker for transcribing audio with faster-whisper."""

    progress = Signal(str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        audio_path,
        model_name="medium.en",
        device="cpu",
        compute_type="int8",
        vad_threshold=0.30,
    ):
        super().__init__()
        self.audio_path = str(audio_path)
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.vad_threshold = vad_threshold

    def run(self):
        try:
            self.progress.emit(f"Loading Whisper model '{self.model_name}'...")
            cache_key = (self.model_name, self.device, self.compute_type)

            global _MODEL_CACHE
            if cache_key in _MODEL_CACHE:
                model = _MODEL_CACHE[cache_key]
            else:
                from faster_whisper import WhisperModel

                model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                _MODEL_CACHE[cache_key] = model

            self.progress.emit("Transcribing audio and aligning words...")
            segments_gen, info = model.transcribe(
                self.audio_path,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters=dict(threshold=self.vad_threshold),
            )

            segments = []
            for seg in segments_gen:
                words = []
                if seg.words:
                    for w in seg.words:
                        words.append(
                            {
                                "word": w.word,
                                "start": round(w.start, 2),
                                "end": round(w.end, 2),
                                "probability": round(w.probability, 2),
                            }
                        )
                segments.append(
                    {
                        "id": seg.id,
                        "start": round(seg.start, 2),
                        "end": round(seg.end, 2),
                        "text": seg.text.strip(),
                        "words": words,
                    }
                )

            self.progress.emit("Transcription complete.")
            self.finished.emit(
                {
                    "model": self.model_name,
                    "language": getattr(info, "language", "en"),
                    "duration": getattr(info, "duration", 0.0),
                    "segments": segments,
                }
            )

        except Exception as exc:
            self.failed.emit(str(exc))
