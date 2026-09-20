from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from src.ui.styles import KPI_CARD_STYLE, PAUSE_BADGE_STYLE, SPEECH_CARD_STYLE


class ReportView(QWidget):
    """Profile report view with audio timeline playback and segment breakdown."""

    seek_requested = Signal(int)  # ms

    def __init__(self, audio_player, session_manager, parent=None):
        super().__init__(parent)
        self.player = audio_player
        self.session_manager = session_manager
        self.current_session = None

        self._user_is_scrubbing = False

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Top Bar: Session Picker
        top_bar = QHBoxLayout()
        lbl_session = QLabel("Session:")
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(280)
        self.session_combo.currentIndexChanged.connect(self._on_session_selected)

        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.clicked.connect(self.refresh_session_list)

        top_bar.addWidget(lbl_session)
        top_bar.addWidget(self.session_combo)
        top_bar.addWidget(self.btn_refresh)
        top_bar.addStretch(1)
        layout.addLayout(top_bar)

        # KPI Cards Row
        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(12)

        self.card_total_time = self._create_kpi_card(
            "Total Time", "--:--", "Elapsed recording"
        )
        self.card_effective_time = self._create_kpi_card(
            "Effective Speech", "--:--", "Up to last spoken word"
        )
        self.card_words = self._create_kpi_card(
            "Word Count", "0", "Total words transcribed"
        )
        self.card_wpm = self._create_kpi_card(
            "Speaking Pace", "0 WPM", "Words per speaking minute"
        )
        self.card_pauses = self._create_kpi_card(
            "Pauses", "0", "Deliberate breaks detected"
        )
        self.card_phone_timer = self._create_kpi_card(
            "Phone Timer", "--:--", "Virtual phone timer"
        )

        self.kpi_layout.addWidget(self.card_total_time)
        self.kpi_layout.addWidget(self.card_effective_time)
        self.kpi_layout.addWidget(self.card_words)
        self.kpi_layout.addWidget(self.card_wpm)
        self.kpi_layout.addWidget(self.card_pauses)
        self.kpi_layout.addWidget(self.card_phone_timer)
        layout.addLayout(self.kpi_layout)

        # Audio Player Bar
        player_frame = QFrame()
        player_frame.setStyleSheet(
            "background-color: #262632; border-radius: 8px; padding: 6px 12px;"
        )
        player_layout = QHBoxLayout(player_frame)

        self.btn_play_pause = QPushButton("Play")
        self.btn_play_pause.setFixedWidth(80)
        self.btn_play_pause.clicked.connect(self.player.toggle_play_pause)

        self.lbl_time_pos = QLabel("00:00 / 00:00")
        self.lbl_time_pos.setFixedWidth(110)

        self.scrubber = QSlider(Qt.Horizontal)
        self.scrubber.setRange(0, 1000)
        self.scrubber.sliderPressed.connect(self._on_scrubber_pressed)
        self.scrubber.sliderReleased.connect(self._on_scrubber_released)
        self.scrubber.sliderMoved.connect(self._on_scrubber_moved)

        lbl_vol = QLabel("Vol:")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(
            lambda v: self.player.set_volume(v / 100.0)
        )

        player_layout.addWidget(self.btn_play_pause)
        player_layout.addWidget(self.lbl_time_pos)
        player_layout.addWidget(self.scrubber, 1)
        player_layout.addWidget(lbl_vol)
        player_layout.addWidget(self.vol_slider)
        layout.addWidget(player_frame)

        # Timeline and Segments List (Scroll Area)
        lbl_segments = QLabel(
            "Speech Segments & Comic Timing (Click any block to seek audio):"
        )
        lbl_segments.setStyleSheet("font-weight: 700; color: #a0a0b8;")
        layout.addWidget(lbl_segments)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.segments_container = QWidget()
        self.segments_layout = QVBoxLayout(self.segments_container)
        self.segments_layout.setContentsMargins(4, 4, 4, 4)
        self.segments_layout.setSpacing(8)
        self.segments_layout.addStretch(1)

        self.scroll_area.setWidget(self.segments_container)
        layout.addWidget(self.scroll_area, 1)

    def _connect_signals(self):
        self.player.position_changed.connect(self._on_player_position_changed)
        self.player.duration_changed.connect(self._on_player_duration_changed)
        self.player.state_changed.connect(self._on_playback_state_changed)

    def _create_kpi_card(self, title, default_val, subtitle):
        card = QFrame()
        card.setStyleSheet(KPI_CARD_STYLE)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "color: #88889a; font-size: 11px; text-transform: uppercase; font-weight: 600;"
        )

        lbl_val = QLabel(default_val)
        lbl_val.setStyleSheet(
            "color: #4daafc; font-size: 20px; font-weight: 700; font-family: monospace;"
        )

        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("color: #6a6a7c; font-size: 10px;")

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        vbox.addWidget(lbl_sub)
        card.value_label = lbl_val
        card.subtitle_label = lbl_sub
        return card

    def refresh_session_list(self):
        sessions = self.session_manager.list_sessions()
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        for sess in sessions:
            sess_id = sess.get("session_id", "unknown")
            dur = sess.get("global_duration_seconds", 0)
            status = sess.get("status", "recorded")
            self.session_combo.addItem(f"{sess_id} ({dur}s, {status})", sess_id)
        self.session_combo.blockSignals(False)
        if sessions:
            self._on_session_selected(0)

    def select_session(self, session_id):
        self.refresh_session_list()
        index = self.session_combo.findData(session_id)
        if index >= 0:
            self.session_combo.setCurrentIndex(index)
            self._on_session_selected(index)

    def _on_session_selected(self, index):
        session_id = self.session_combo.itemData(index)
        if not session_id:
            return
        session_data = self.session_manager.load_session(session_id)
        if session_data:
            self.display_session(session_data)

    def display_session(self, session_data):
        self.current_session = session_data
        audio_path = self.session_manager.get_audio_path(session_data.get("session_id"))
        if audio_path.exists():
            self.player.load(str(audio_path))

        profile = session_data.get("profile") or {}

        tot_sec = session_data.get("global_duration_seconds", 0.0)
        eff_sec = profile.get("effective_duration_seconds", tot_sec)
        words = profile.get("total_words", 0)
        wpm = profile.get("speaking_pace_wpm", 0.0)
        pauses_cnt = profile.get("pauses_count", 0)
        pause_sec = profile.get("total_pause_time_seconds", 0.0)

        self.card_total_time.value_label.setText(self._format_seconds(tot_sec))
        self.card_effective_time.value_label.setText(self._format_seconds(eff_sec))
        self.card_words.value_label.setText(str(words))
        self.card_wpm.value_label.setText(f"{wpm} WPM")
        self.card_pauses.value_label.setText(f"{pauses_cnt} ({round(pause_sec, 1)}s)")

        # Update phone timer card
        pt_info = session_data.get("phone_timer") or {}
        starts = pt_info.get("starts", [])
        if not starts and pt_info.get("start_time_seconds") is not None:
            starts = [
                {
                    "start_time_seconds": pt_info["start_time_seconds"],
                    "duration_seconds": pt_info.get("duration_seconds", 180),
                }
            ]

        if not starts or not pt_info.get("used", True):
            self.card_phone_timer.value_label.setText("None")
            self.card_phone_timer.subtitle_label.setText("Not started in speech")
        elif len(starts) == 1:
            st = starts[0].get("start_time_seconds", 0.0)
            dur = starts[0].get("duration_seconds", 180)
            self.card_phone_timer.value_label.setText(self._format_seconds(st))
            self.card_phone_timer.subtitle_label.setText(
                f"Start: {self._format_seconds(st)} • Alarm: {self._format_seconds(st + dur)}"
            )
        else:
            self.card_phone_timer.value_label.setText(f"{len(starts)} Starts")
            st_list = ", ".join(
                [self._format_seconds(s.get("start_time_seconds", 0)) for s in starts]
            )
            self.card_phone_timer.subtitle_label.setText(f"Starts: {st_list}")

        # Clear existing timeline items
        while self.segments_layout.count() > 1:
            child = self.segments_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        timeline_items = profile.get("timeline_items", [])
        if not timeline_items:
            lbl_empty = QLabel(
                "No speech segments available yet for this session. (Transcription may still be in progress or pending)."
            )
            lbl_empty.setStyleSheet("color: #88889a; padding: 20px;")
            self.segments_layout.insertWidget(0, lbl_empty)
            return

        for idx, item in enumerate(timeline_items):
            itype = item.get("type")
            if itype == "pause":
                widget = self._create_pause_card(item)
            elif itype in ("phone_timer_start", "phone_timer_alarm"):
                widget = self._create_phone_timer_event_card(item)
            else:
                widget = self._create_speech_card(item)
            self.segments_layout.insertWidget(idx, widget)

    def _create_phone_timer_event_card(self, item):
        frame = QFrame()
        itype = item.get("type")
        is_start = itype == "phone_timer_start"

        if is_start:
            frame.setStyleSheet(
                "background-color: #241c30; border: 1px solid #7e57c2; border-radius: 6px; padding: 8px 14px;"
            )
            lbl_color = "#ce93d8"
            icon = "📱"
        else:
            frame.setStyleSheet(
                "background-color: #38241b; border: 1px solid #f57c00; border-radius: 6px; padding: 8px 14px;"
            )
            lbl_color = "#ffb74d"
            icon = "🔔"

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)

        start = item.get("start", 0.0)
        label_text = item.get("label", "Phone Timer Event")
        lbl_text = QLabel(f"{icon} {label_text} at {self._format_seconds(start)}")
        lbl_text.setStyleSheet(
            f"color: {lbl_color}; font-weight: 600; font-size: 13px;"
        )

        btn_jump = QPushButton("Play Here")
        btn_jump.setFixedWidth(90)
        btn_jump.clicked.connect(lambda: self.player.seek(int(start * 1000)))

        layout.addWidget(lbl_text, 1)
        layout.addWidget(btn_jump)
        return frame

    def _create_pause_card(self, item):
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #242219; border: 1px dashed #7a5e20; border-radius: 6px; padding: 8px 14px;"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)

        dur = item.get("duration", 0.0)
        start = item.get("start", 0.0)
        lbl_text = QLabel(
            f"⏸ Pause: {round(dur, 1)}s  (at {self._format_seconds(start)}) — audience reaction / comic timing"
        )
        lbl_text.setStyleSheet("color: #ffca28; font-weight: 600; font-size: 13px;")

        btn_jump = QPushButton("Play Pause")
        btn_jump.setFixedWidth(90)
        btn_jump.clicked.connect(lambda: self.player.seek(int(start * 1000)))

        layout.addWidget(lbl_text, 1)
        layout.addWidget(btn_jump)
        return frame

    def _create_speech_card(self, item):
        frame = QFrame()
        frame.setStyleSheet(SPEECH_CARD_STYLE)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header row: timestamp, duration, wpm, and seek button
        hdr_row = QHBoxLayout()
        start = item.get("start", 0.0)
        end = item.get("end", 0.0)
        dur = item.get("duration", 0.0)
        wpm = item.get("wpm", 0.0)
        wcnt = item.get("word_count", 0)

        lbl_badge = QLabel(
            f"{self._format_seconds(start)} - {self._format_seconds(end)} ({round(dur, 1)}s)"
        )
        lbl_badge.setStyleSheet(
            "background-color: #1a2738; color: #4daafc; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px;"
        )

        lbl_pace = QLabel(f"{wcnt} words • {wpm} WPM")
        lbl_pace.setStyleSheet("color: #9999a8; font-size: 12px;")

        btn_seek = QPushButton("Play Here")
        btn_seek.setFixedWidth(80)
        btn_seek.clicked.connect(lambda: self.player.seek(int(start * 1000)))

        hdr_row.addWidget(lbl_badge)
        hdr_row.addWidget(lbl_pace)
        hdr_row.addStretch(1)
        hdr_row.addWidget(btn_seek)

        lbl_text = QLabel(item.get("text", ""))
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet(
            "color: #e6e6e6; font-size: 14px; line-height: 1.4; padding-top: 2px;"
        )

        layout.addLayout(hdr_row)
        layout.addWidget(lbl_text)

        # Clicking anywhere on the card seeks to this segment
        frame.mousePressEvent = lambda e: self.player.seek(int(start * 1000))
        frame.setCursor(Qt.PointingHandCursor)

        return frame

    def _format_seconds(self, sec):
        sec = max(0, int(sec))
        m = sec // 60
        s = sec % 60
        return f"{m:02d}:{s:02d}"

    def _on_player_position_changed(self, pos_ms):
        if not self._user_is_scrubbing:
            dur_ms = self.player.player.duration()
            if dur_ms > 0:
                self.scrubber.setValue(int((pos_ms / dur_ms) * 1000))
            self.lbl_time_pos.setText(
                f"{self._format_seconds(pos_ms / 1000)} / {self._format_seconds(dur_ms / 1000)}"
            )

    def _on_player_duration_changed(self, dur_ms):
        pos_ms = self.player.player.position()
        self.lbl_time_pos.setText(
            f"{self._format_seconds(pos_ms / 1000)} / {self._format_seconds(dur_ms / 1000)}"
        )

    def _on_playback_state_changed(self, is_playing):
        self.btn_play_pause.setText("Pause" if is_playing else "Play")

    def _on_scrubber_pressed(self):
        self._user_is_scrubbing = True

    def _on_scrubber_released(self):
        self._user_is_scrubbing = False
        dur_ms = self.player.player.duration()
        if dur_ms > 0:
            target_ms = int((self.scrubber.value() / 1000.0) * dur_ms)
            self.player.seek(target_ms)

    def _on_scrubber_moved(self, val):
        dur_ms = self.player.player.duration()
        if dur_ms > 0:
            current_sec = (val / 1000.0) * (dur_ms / 1000.0)
            self.lbl_time_pos.setText(
                f"{self._format_seconds(current_sec)} / {self._format_seconds(dur_ms / 1000)}"
            )
