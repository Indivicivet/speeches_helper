from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from src.audio.beeper import PhoneBeeper
from src.audio.player import AudioPlayer
from src.audio.recorder import AudioRecorder
from src.core.profiler import SpeechProfiler
from src.core.session_manager import SessionManager
from src.core.transcriber import TranscriberThread
from src.ui.compare_view import CompareView
from src.ui.practice_view import PracticeView
from src.ui.report_view import ReportView
from src.ui.styles import APP_STYLESHEET


class MainWindow(QMainWindow):
    """Main application window managing tabs, audio recording, and background tasks."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Speeches Helper — Speech & Blind Timer Practice")
        self.setMinimumSize(850, 520)
        self.resize(920, 720)

        self.session_manager = SessionManager("sessions")
        self.beeper = PhoneBeeper()
        self.recorder = AudioRecorder()
        self.player = AudioPlayer()

        self.current_session_id = None
        self.current_pause_threshold = 1.5
        self.transcriber_thread = None
        self.transcription_queue = []
        self.current_transcription_job = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setStyleSheet(APP_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)

        self.tabs = QTabWidget()
        self.practice_view = PracticeView(self.beeper)
        self.report_view = ReportView(self.player, self.session_manager)
        self.compare_view = CompareView(self.session_manager)

        self.tabs.addTab(self.practice_view, "Rehearsal & Timers")
        self.tabs.addTab(self.report_view, "Profile Report")
        self.tabs.addTab(self.compare_view, "Compare Speeches")

        layout.addWidget(self.tabs)

    def _connect_signals(self):
        self.practice_view.speech_started.connect(self._on_speech_started)
        self.practice_view.speech_stopped.connect(self._on_speech_stopped)
        self.recorder.level_changed.connect(self.practice_view.set_mic_level)
        self.recorder.initial_audio_missing.connect(
            self.practice_view.show_audio_warning
        )
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        if index == 1:
            self.report_view.refresh_session_list()
        elif index == 2:
            self.compare_view.refresh_session_lists()

    def _on_speech_started(self, model_name, pause_threshold):
        self.current_session_id = self.session_manager.generate_session_id()
        self.current_pause_threshold = pause_threshold
        try:
            self.recorder.start()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Microphone Error",
                f"Could not initialize audio input device:\n{exc}",
            )
            self.practice_view.stop_speech()

    def _on_speech_stopped(self, metadata):
        session_id = self.current_session_id
        if not session_id:
            return

        mp3_path = self.session_manager.get_audio_path(session_id)
        try:
            self.recorder.stop(mp3_path)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Audio Export Warning",
                f"Recorded audio could not be exported to {mp3_path}:\n{exc}",
            )

        has_initial_audio = self.recorder.has_initial_audio()

        # Fail-safe save: persist initial session metadata to disk immediately
        self.session_manager.save_initial_session(
            session_id=session_id,
            global_duration_seconds=metadata["global_duration_seconds"],
            phone_timer_used=metadata["phone_timer_used"],
            phone_timer_duration=metadata["phone_timer_duration"],
            phone_timer_start_time=metadata["phone_timer_start_time"],
            phone_timer_starts=metadata.get("phone_timer_starts", []),
            peek_events=metadata["peek_events"],
            has_initial_audio=has_initial_audio,
        )

        # Queue transcription job
        job = {
            "session_id": session_id,
            "mp3_path": mp3_path,
            "model_name": metadata.get("model_name", "medium.en"),
            "pause_threshold": metadata.get("pause_threshold", 1.5),
            "global_duration_seconds": metadata["global_duration_seconds"],
            "phone_timer_data": {
                "used": metadata["phone_timer_used"],
                "duration_seconds": metadata["phone_timer_duration"],
                "start_time_seconds": metadata["phone_timer_start_time"],
                "starts": metadata.get("phone_timer_starts", []),
            },
            "has_initial_audio": has_initial_audio,
        }
        self.transcription_queue.append(job)
        self._process_next_transcription()

    def _process_next_transcription(self):
        if self.current_transcription_job is not None or not self.transcription_queue:
            return

        job = self.transcription_queue.pop(0)
        self.current_transcription_job = job

        remaining = len(self.transcription_queue)
        queue_suffix = f" ({remaining} queued)" if remaining > 0 else ""
        self.practice_view.set_transcription_status(
            f"Transcribing speech '{job['session_id']}' with '{job['model_name']}'{queue_suffix}...",
            in_progress=True,
        )

        thread = TranscriberThread(
            audio_path=job["mp3_path"], model_name=job["model_name"]
        )
        self.transcriber_thread = thread

        def on_progress(msg):
            cur_job = self.current_transcription_job
            rem = len(self.transcription_queue)
            q_info = f" [{rem} queued]" if rem > 0 else ""
            prefix = f"[{cur_job['session_id']}]{q_info} " if cur_job else ""
            self.practice_view.set_transcription_status(
                f"{prefix}{msg}", in_progress=True
            )

        thread.progress.connect(on_progress)
        thread.finished.connect(
            lambda res, j=job: self._on_transcription_finished(
                session_id=j["session_id"],
                trans_result=res,
                global_duration=j["global_duration_seconds"],
                pause_threshold=j["pause_threshold"],
                phone_timer_data=j["phone_timer_data"],
                has_initial_audio=j["has_initial_audio"],
            )
        )
        thread.failed.connect(
            lambda err, j=job: self._on_transcription_failed(
                session_id=j["session_id"], error_msg=err
            )
        )
        thread.start()

    def _on_transcription_finished(
        self,
        session_id,
        trans_result,
        global_duration,
        pause_threshold,
        phone_timer_data=None,
        has_initial_audio=None,
    ):
        profiler = SpeechProfiler(pause_threshold_seconds=pause_threshold)
        profile_data = profiler.analyze(
            segments=trans_result.get("segments", []),
            global_duration_seconds=global_duration,
            phone_timer_data=phone_timer_data,
        )

        # Update session file with full profile and transcription
        self.session_manager.update_transcription_and_profile(
            session_id=session_id,
            transcription_data=trans_result,
            profile_data=profile_data,
            has_initial_audio=has_initial_audio,
        )

        # Refresh report list so new session is available in Report view dropdown
        self.report_view.refresh_session_list()

        self.current_transcription_job = None
        self.transcriber_thread = None

        if self.transcription_queue:
            self._process_next_transcription()
        else:
            self.practice_view.set_transcription_status(
                "Speech processed and profiled.", in_progress=False
            )

    def _on_transcription_failed(self, session_id, error_msg):
        self.current_transcription_job = None
        self.transcriber_thread = None

        if self.transcription_queue:
            self._process_next_transcription()
        else:
            self.practice_view.set_transcription_status(
                f"Transcription error: {error_msg}. Audio and baseline session saved.",
                in_progress=False,
            )

        QMessageBox.warning(
            self,
            "Transcription Failed",
            f"Whisper transcription failed for {session_id}:\n{error_msg}\n\nYour audio recording is preserved in ./sessions.",
        )

    def keyPressEvent(self, event):
        # Forward hotkeys if on practice tab
        if self.tabs.currentIndex() == 0:
            handled = self.practice_view.handle_key_press(event)
            if handled:
                event.accept()
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.tabs.currentIndex() == 0:
            handled = self.practice_view.handle_key_release(event)
            if handled:
                event.accept()
                return
        super().keyReleaseEvent(event)

    def closeEvent(self, event):
        self.player.stop()
        self.beeper.stop_alarm()
        if self.recorder.is_recording:
            self.recorder.is_recording = False
        event.accept()
