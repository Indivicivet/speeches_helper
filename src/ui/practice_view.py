import time
from PySide6.QtCore import QTime, QTimer, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PracticeView(QWidget):
    """Practice recording view with global timer, virtual phone timer, and blind peeking."""

    speech_started = Signal(str, float)  # model_name, pause_threshold
    speech_stopped = Signal(dict)  # session timings metadata
    transcription_requested = Signal(str, str, float)  # session_id, model, pause_thresh

    def __init__(self, beeper, parent=None):
        super().__init__(parent)
        self.beeper = beeper

        self.is_speaking = False
        self.global_start_time = None
        self.global_elapsed_seconds = 0.0

        self.phone_timer_active = False
        self.phone_timer_start_time = None
        self.phone_duration_seconds = 180
        self.phone_remaining_seconds = 180
        self.phone_timer_starts = []

        self.peek_global_active = False
        self.peek_phone_active = False
        self.peek_events = []

        # Ticking timer (every 100ms for smooth display)
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(100)
        self.tick_timer.timeout.connect(self._on_tick)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Config Row
        config_layout = QHBoxLayout()
        config_layout.setSpacing(16)

        lbl_model = QLabel("Whisper Model:")
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(["medium.en", "small.en", "large-v3", "base.en"])
        self.model_combo.setCurrentText("medium.en")

        lbl_pause = QLabel("Pause Threshold (s):")
        self.pause_spin = QDoubleSpinBox()
        self.pause_spin.setRange(0.5, 10.0)
        self.pause_spin.setSingleStep(0.1)
        self.pause_spin.setValue(1.5)

        config_layout.addWidget(lbl_model)
        config_layout.addWidget(self.model_combo, 1)
        config_layout.addWidget(lbl_pause)
        config_layout.addWidget(self.pause_spin)
        config_layout.addStretch(1)

        main_layout.addLayout(config_layout)

        # Timers Layout (Side by Side)
        timers_layout = QHBoxLayout()
        timers_layout.setSpacing(20)

        # --- Global Timer Group ---
        global_group = QGroupBox("Global Speech Timer")
        global_vbox = QVBoxLayout(global_group)
        global_vbox.setSpacing(12)

        self.chk_hide_global = QCheckBox("Hide Timer (Blind Practice)")
        self.chk_hide_global.setChecked(True)
        self.chk_hide_global.stateChanged.connect(self._update_display)

        self.lbl_global_timer = QLabel("00:00")
        self.lbl_global_timer.setObjectName("timer_display")

        self.btn_peek_global = QPushButton("Peek Global Timer (Hold 1)")
        self.btn_peek_global.setObjectName("btn_peek")
        self.btn_peek_global.pressed.connect(self._on_peek_global_press)
        self.btn_peek_global.released.connect(self._on_peek_global_release)

        global_vbox.addWidget(self.chk_hide_global)
        global_vbox.addWidget(self.lbl_global_timer)
        global_vbox.addWidget(self.btn_peek_global)

        # --- Phone Timer Group ---
        phone_group = QGroupBox("Virtual Phone Timer")
        phone_vbox = QVBoxLayout(phone_group)
        phone_vbox.setSpacing(12)

        phone_header = QHBoxLayout()
        self.chk_hide_phone = QCheckBox("Hide Phone Timer")
        self.chk_hide_phone.setChecked(True)
        self.chk_hide_phone.stateChanged.connect(self._update_display)

        phone_dur_lbl = QLabel("Set (m:s):")
        self.phone_min_spin = QSpinBox()
        self.phone_min_spin.setRange(0, 59)
        self.phone_min_spin.setValue(3)

        self.phone_sec_spin = QSpinBox()
        self.phone_sec_spin.setRange(0, 59)
        self.phone_sec_spin.setValue(0)

        phone_header.addWidget(self.chk_hide_phone)
        phone_header.addStretch(1)
        phone_header.addWidget(phone_dur_lbl)
        phone_header.addWidget(self.phone_min_spin)
        phone_header.addWidget(QLabel(":"))
        phone_header.addWidget(self.phone_sec_spin)

        self.lbl_phone_timer = QLabel("03:00")
        self.lbl_phone_timer.setObjectName("phone_timer_display")

        phone_btn_row = QHBoxLayout()
        self.btn_start_phone = QPushButton("Start Phone Timer (T)")
        self.btn_start_phone.clicked.connect(self.start_phone_timer)

        self.btn_stop_alarm = QPushButton("Stop Timer / Alarm (S)")
        self.btn_stop_alarm.setObjectName("btn_alarm_stop")
        self.btn_stop_alarm.clicked.connect(self.stop_timer_or_alarm)

        phone_btn_row.addWidget(self.btn_start_phone)
        phone_btn_row.addWidget(self.btn_stop_alarm)

        self.btn_peek_phone = QPushButton("Peek Phone Timer (Hold 2)")
        self.btn_peek_phone.setObjectName("btn_peek")
        self.btn_peek_phone.pressed.connect(self._on_peek_phone_press)
        self.btn_peek_phone.released.connect(self._on_peek_phone_release)

        self.lbl_phone_status = QLabel("Status: Ready to start")
        self.lbl_phone_status.setAlignment(Qt.AlignCenter)
        self.lbl_phone_status.setStyleSheet(
            "color: #a0a0b0; font-size: 12px; font-weight: 600; padding: 2px;"
        )

        phone_vbox.addLayout(phone_header)
        phone_vbox.addWidget(self.lbl_phone_timer)
        phone_vbox.addWidget(self.lbl_phone_status)
        phone_vbox.addLayout(phone_btn_row)
        phone_vbox.addWidget(self.btn_peek_phone)

        timers_layout.addWidget(global_group, 1)
        timers_layout.addWidget(phone_group, 1)
        main_layout.addLayout(timers_layout)

        # Mic level indicator
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Mic Activity:"))
        self.mic_bar = QProgressBar()
        self.mic_bar.setRange(0, 100)
        self.mic_bar.setValue(0)
        self.mic_bar.setTextVisible(False)
        self.mic_bar.setFixedHeight(8)
        mic_layout.addWidget(self.mic_bar)
        main_layout.addLayout(mic_layout)

        self.btn_peek_global.setFocusPolicy(Qt.NoFocus)
        self.btn_start_phone.setFocusPolicy(Qt.NoFocus)
        self.btn_stop_alarm.setFocusPolicy(Qt.NoFocus)
        self.btn_peek_phone.setFocusPolicy(Qt.NoFocus)
        self.chk_hide_global.setFocusPolicy(Qt.NoFocus)
        self.chk_hide_phone.setFocusPolicy(Qt.NoFocus)

        # Rehearsal shortcuts that trigger regardless of focused widget
        QShortcut(QKeySequence(Qt.Key_T), self, self.start_phone_timer)
        QShortcut(QKeySequence(Qt.Key_S), self, self.stop_timer_or_alarm)
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_speech)
        QShortcut(QKeySequence(Qt.Key_Return), self, self.toggle_speech)

        # Primary Control Button
        self.btn_toggle_speech = QPushButton("Begin Speech (Space / Enter)")
        self.btn_toggle_speech.setObjectName("btn_record_start")
        self.btn_toggle_speech.setFocusPolicy(Qt.NoFocus)
        self.btn_toggle_speech.clicked.connect(self.toggle_speech)
        main_layout.addWidget(self.btn_toggle_speech)

        # Status & Progress Label
        self.lbl_status = QLabel("Ready to practice. Press Begin Speech to start.")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.lbl_status)

        self.transcription_progress = QProgressBar()
        self.transcription_progress.setRange(0, 0)  # Indeterminate
        self.transcription_progress.setVisible(False)
        main_layout.addWidget(self.transcription_progress)

        self._update_display()

    def set_mic_level(self, level):
        """Sets mic progress bar value (0.0 to 1.0)."""
        self.mic_bar.setValue(int(level * 100))

    def _format_time(self, total_seconds):
        total_seconds = max(0, int(total_seconds))
        mins = total_seconds // 60
        secs = total_seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def _update_display(self):
        # Global display
        if self.chk_hide_global.isChecked() and not self.peek_global_active:
            self.lbl_global_timer.setText("••:••")
            self.lbl_global_timer.setObjectName("timer_display_hidden")
        else:
            self.lbl_global_timer.setText(
                self._format_time(self.global_elapsed_seconds)
            )
            self.lbl_global_timer.setObjectName("timer_display")
        self.lbl_global_timer.setStyle(self.lbl_global_timer.style())

        # Phone display
        if self.chk_hide_phone.isChecked() and not self.peek_phone_active:
            self.lbl_phone_timer.setText("••:••")
            self.lbl_phone_timer.setObjectName("timer_display_hidden")
        else:
            self.lbl_phone_timer.setText(
                self._format_time(self.phone_remaining_seconds)
            )
            self.lbl_phone_timer.setObjectName("phone_timer_display")
        self.lbl_phone_timer.setStyle(self.lbl_phone_timer.style())

    def _on_tick(self):
        now = time.time()
        if self.is_speaking and self.global_start_time:
            self.global_elapsed_seconds = now - self.global_start_time

        if self.phone_timer_active and self.phone_timer_start_time:
            phone_elapsed = now - self.phone_timer_start_time
            self.phone_remaining_seconds = max(
                0.0, self.phone_duration_seconds - phone_elapsed
            )

            # Check if alarm should trigger
            if self.phone_remaining_seconds <= 0.0:
                if not self.beeper.is_alarming():
                    self.beeper.start_alarm()
                    self.btn_stop_alarm.setEnabled(True)
                self.lbl_phone_status.setText("🔔 ALARM RINGING! Press Stop Alarm (S)")
                self.lbl_phone_status.setStyleSheet(
                    "color: #ff5252; font-size: 12px; font-weight: 700; padding: 2px;"
                )
            else:
                last_start = (
                    self.phone_timer_starts[-1]["start_time_seconds"]
                    if self.phone_timer_starts
                    else 0.0
                )
                self.lbl_phone_status.setText(
                    f"● RUNNING (Started at {self._format_time(last_start)})"
                )
                self.lbl_phone_status.setStyleSheet(
                    "color: #ffd54f; font-size: 12px; font-weight: 700; padding: 2px;"
                )

        self._update_display()

    def start_phone_timer(self):
        self.phone_duration_seconds = (
            self.phone_min_spin.value() * 60 + self.phone_sec_spin.value()
        )
        self.phone_remaining_seconds = self.phone_duration_seconds
        self.phone_timer_start_time = time.time()
        self.phone_timer_active = True

        current_offset = (
            round(time.time() - self.global_start_time, 2)
            if self.is_speaking and self.global_start_time
            else 0.0
        )
        self.phone_timer_starts.append(
            {
                "start_time_seconds": current_offset,
                "duration_seconds": self.phone_duration_seconds,
                "alarm_time_seconds": round(
                    current_offset + self.phone_duration_seconds, 2
                ),
            }
        )

        if not self.tick_timer.isActive():
            self.tick_timer.start()

        self.btn_start_phone.setText("Restart Phone Timer (T)")
        self.lbl_phone_status.setText(
            f"● RUNNING (Started at {self._format_time(current_offset)})"
        )
        self.lbl_phone_status.setStyleSheet(
            "color: #ffd54f; font-size: 12px; font-weight: 700; padding: 2px;"
        )

        if not self.is_speaking:
            self.lbl_status.setText(
                "Phone timer active. Press Begin Speech when you want to start talking."
            )
        else:
            self.lbl_status.setText(
                f"Phone timer running ({self._format_time(self.phone_duration_seconds)} countdown)."
            )
        self._update_display()

    def stop_timer_or_alarm(self):
        was_running = self.phone_timer_active
        was_alarming = self.beeper.is_alarming()

        self.beeper.stop_alarm()
        self.phone_timer_active = False
        self.phone_duration_seconds = (
            self.phone_min_spin.value() * 60 + self.phone_sec_spin.value()
        )
        self.phone_remaining_seconds = self.phone_duration_seconds
        self.btn_start_phone.setText("Start Phone Timer (T)")

        if was_alarming:
            self.lbl_phone_status.setText("○ Alarm silenced")
            self.lbl_phone_status.setStyleSheet(
                "color: #a0a0b0; font-size: 12px; font-weight: 600; padding: 2px;"
            )
        elif was_running:
            self.lbl_phone_status.setText("○ Timer stopped")
            self.lbl_phone_status.setStyleSheet(
                "color: #a0a0b0; font-size: 12px; font-weight: 600; padding: 2px;"
            )
            if self.is_speaking:
                self.lbl_status.setText("Phone timer stopped.")
        else:
            self.lbl_phone_status.setText("Status: Ready to start")

        self._update_display()

    # Backwards compatibility alias
    silence_alarm = stop_timer_or_alarm

    def _on_peek_global_press(self):
        self.peek_global_active = True
        self.peek_events.append(
            {"timer": "global", "time": round(self.global_elapsed_seconds, 2)}
        )
        self._update_display()

    def _on_peek_global_release(self):
        self.peek_global_active = False
        self._update_display()

    def _on_peek_phone_press(self):
        self.peek_phone_active = True
        self.peek_events.append(
            {"timer": "phone", "time": round(self.global_elapsed_seconds, 2)}
        )
        self._update_display()

    def _on_peek_phone_release(self):
        self.peek_phone_active = False
        self._update_display()

    def toggle_speech(self):
        if not self.is_speaking:
            self.start_speech()
        else:
            self.stop_speech()

    def start_speech(self):
        self.is_speaking = True
        self.global_start_time = time.time()
        self.global_elapsed_seconds = 0.0

        # Reset phone timer display
        self.phone_timer_active = False
        self.phone_timer_start_time = None
        self.phone_duration_seconds = (
            self.phone_min_spin.value() * 60 + self.phone_sec_spin.value()
        )
        self.phone_remaining_seconds = self.phone_duration_seconds
        self.phone_timer_starts = []
        self.peek_events = []

        self.btn_start_phone.setText("Start Phone Timer (T)")
        self.lbl_phone_status.setText("Status: Ready to start")
        self.lbl_phone_status.setStyleSheet(
            "color: #a0a0b0; font-size: 12px; font-weight: 600; padding: 2px;"
        )

        self.silence_alarm()
        self.tick_timer.start()

        self.btn_toggle_speech.setText("Stop Speech (Space / Enter)")
        self.btn_toggle_speech.setObjectName("btn_record_stop")
        self.btn_toggle_speech.setStyle(self.btn_toggle_speech.style())
        self.lbl_status.setText("Recording in progress...")

        model_name = self.model_combo.currentText().strip()
        pause_thresh = self.pause_spin.value()
        self.speech_started.emit(model_name, pause_thresh)
        self._update_display()

    def stop_speech(self):
        self.is_speaking = False
        self.tick_timer.stop()
        self.silence_alarm()
        self.mic_bar.setValue(0)

        self.btn_toggle_speech.setText("Begin Speech (Space / Enter)")
        self.btn_toggle_speech.setObjectName("btn_record_start")
        self.btn_toggle_speech.setStyle(self.btn_toggle_speech.style())
        self.lbl_status.setText(
            "Speech recorded. Saving audio and preparing transcription..."
        )

        metadata = {
            "global_duration_seconds": self.global_elapsed_seconds,
            "phone_timer_used": len(self.phone_timer_starts) > 0,
            "phone_timer_duration": self.phone_duration_seconds,
            "phone_timer_start_time": (
                self.phone_timer_starts[0]["start_time_seconds"]
                if self.phone_timer_starts
                else None
            ),
            "phone_timer_starts": self.phone_timer_starts,
            "peek_events": self.peek_events,
            "model_name": self.model_combo.currentText().strip(),
            "pause_threshold": self.pause_spin.value(),
        }
        self.speech_stopped.emit(metadata)

    def set_transcription_status(self, text, in_progress=True):
        self.lbl_status.setText(text)
        self.transcription_progress.setVisible(in_progress)

    def handle_key_press(self, event):
        """Processes global hotkeys for hands-free rehearsal."""
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.toggle_speech()
            return True
        elif key == Qt.Key_T:
            self.start_phone_timer()
            return True
        elif key == Qt.Key_S:
            self.silence_alarm()
            return True
        elif key == Qt.Key_1:
            self._on_peek_global_press()
            return True
        elif key == Qt.Key_2:
            self._on_peek_phone_press()
            return True
        return False

    def handle_key_release(self, event):
        key = event.key()
        if key == Qt.Key_1:
            self._on_peek_global_release()
            return True
        elif key == Qt.Key_2:
            self._on_peek_phone_release()
            return True
        return False
