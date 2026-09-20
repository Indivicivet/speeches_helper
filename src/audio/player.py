from pathlib import Path
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlayer(QObject):
    """Audio player wrapping PySide6 QMediaPlayer."""

    position_changed = Signal(int)  # ms
    duration_changed = Signal(int)  # ms
    state_changed = Signal(bool)  # True if playing, False otherwise

    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)

        self.player.positionChanged.connect(self.position_changed.emit)
        self.player.durationChanged.connect(self.duration_changed.emit)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _on_playback_state_changed(self, state):
        self.state_changed.emit(state == QMediaPlayer.PlaybackState.PlayingState)

    def load(self, audio_file_path):
        path = Path(audio_file_path)
        if path.exists():
            self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()

    def stop(self):
        self.player.stop()

    def seek(self, position_ms):
        self.player.setPosition(int(position_ms))

    def set_volume(self, volume_float):
        self.audio_output.setVolume(max(0.0, min(1.0, float(volume_float))))

    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
