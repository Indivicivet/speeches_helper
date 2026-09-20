from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from src.core.diff_matcher import FuzzyDiffMatcher
from src.ui.styles import DIFF_STYLES


class CompareView(QWidget):
    """Side-by-side speech comparison view with fuzzy diff tinting."""

    def __init__(self, session_manager, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.diff_matcher = FuzzyDiffMatcher()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Top Bar: Session Selectors
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        lbl_a = QLabel("Session A:")
        self.combo_a = QComboBox()
        self.combo_a.setMinimumWidth(220)

        lbl_b = QLabel("Session B:")
        self.combo_b = QComboBox()
        self.combo_b.setMinimumWidth(220)

        btn_compare = QPushButton("Compare Sessions")
        btn_compare.clicked.connect(self.run_comparison)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_session_lists)

        top_bar.addWidget(lbl_a)
        top_bar.addWidget(self.combo_a)
        top_bar.addWidget(lbl_b)
        top_bar.addWidget(self.combo_b)
        top_bar.addWidget(btn_compare)
        top_bar.addWidget(btn_refresh)
        top_bar.addStretch(1)
        layout.addLayout(top_bar)

        # Single Scroll Area containing Metrics, Legend, and Side-by-Side Segments
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_layout.setSpacing(14)

        # Comparative Summary Grid
        self.metrics_frame = QFrame()
        self.metrics_frame.setStyleSheet(
            "background-color: #24242e; border: 1px solid #333342; border-radius: 8px; padding: 10px;"
        )
        self.metrics_layout = QGridLayout(self.metrics_frame)
        self.metrics_layout.setContentsMargins(8, 8, 8, 8)
        self.metrics_layout.setSpacing(8)
        self.scroll_layout.addWidget(self.metrics_frame)

        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Fuzzy Match Key:"))

        lbl_leg_sim = QLabel(" Similar Phrasing ")
        lbl_leg_sim.setStyleSheet(
            "background-color: #1b3820; color: #a5d6a7; border-radius: 4px; padding: 2px 6px;"
        )

        lbl_leg_mod = QLabel(" Modified Phrasing ")
        lbl_leg_mod.setStyleSheet(
            "background-color: #2b2b36; color: #ffffff; border-radius: 4px; padding: 2px 6px;"
        )

        lbl_leg_diff = QLabel(" Divergent / New ")
        lbl_leg_diff.setStyleSheet(
            "background-color: #3b1e22; color: #ef9a9a; border-radius: 4px; padding: 2px 6px;"
        )

        lbl_leg_gap = QLabel(" Gap / Inserted ")
        lbl_leg_gap.setStyleSheet(
            "background-color: #24242e; border: 1px dashed #48485a; color: #a0a0b0; border-radius: 4px; padding: 2px 6px;"
        )

        legend_layout.addWidget(lbl_leg_sim)
        legend_layout.addWidget(lbl_leg_mod)
        legend_layout.addWidget(lbl_leg_diff)
        legend_layout.addWidget(lbl_leg_gap)
        legend_layout.addStretch(1)
        self.scroll_layout.addLayout(legend_layout)

        # Side-by-Side Dual-Column Segments
        self.diff_container = QWidget()
        self.diff_layout = QVBoxLayout(self.diff_container)
        self.diff_layout.setContentsMargins(0, 0, 0, 0)
        self.diff_layout.setSpacing(10)
        self.diff_layout.addStretch(1)
        self.scroll_layout.addWidget(self.diff_container)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

    def refresh_session_lists(self):
        sessions = self.session_manager.list_sessions()
        self.combo_a.clear()
        self.combo_b.clear()

        for sess in sessions:
            sess_id = sess.get("session_id", "unknown")
            dur = sess.get("global_duration_seconds", 0)
            text = f"{sess_id} ({dur}s)"
            self.combo_a.addItem(text, sess_id)
            self.combo_b.addItem(text, sess_id)

        if len(sessions) >= 2:
            self.combo_a.setCurrentIndex(1)
            self.combo_b.setCurrentIndex(0)
        elif len(sessions) == 1:
            self.combo_a.setCurrentIndex(0)
            self.combo_b.setCurrentIndex(0)

    def run_comparison(self):
        sess_a_id = self.combo_a.currentData()
        sess_b_id = self.combo_b.currentData()
        if not sess_a_id or not sess_b_id:
            return

        session_a = self.session_manager.load_session(sess_a_id)
        session_b = self.session_manager.load_session(sess_b_id)
        if not session_a or not session_b:
            return

        result = self.diff_matcher.compare_sessions(session_a, session_b)
        self._display_comparison(result)

    def _display_comparison(self, result):
        metrics = result["metrics"]
        aligned_pairs = result["aligned_pairs"]

        # Clear existing metrics grid
        while self.metrics_layout.count() > 0:
            child = self.metrics_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Build metrics table
        headers = ["Metric", "Session A", "Session B", "Difference"]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet(
                "color: #88889a; font-weight: 700; text-transform: uppercase; font-size: 11px;"
            )
            self.metrics_layout.addWidget(lbl, 0, col)

        rows = [
            (
                "Duration",
                f"{metrics['duration_a']}s",
                f"{metrics['duration_b']}s",
                f"{'+' if metrics['duration_delta'] > 0 else ''}{metrics['duration_delta']}s",
            ),
            (
                "Word Count",
                str(metrics["words_a"]),
                str(metrics["words_b"]),
                f"{'+' if metrics['words_delta'] > 0 else ''}{metrics['words_delta']}",
            ),
            (
                "Overall WPM (Total Time)",
                f"{metrics.get('overall_wpm_a', metrics['wpm_a'])} WPM",
                f"{metrics.get('overall_wpm_b', metrics['wpm_b'])} WPM",
                f"{'+' if metrics.get('overall_wpm_delta', 0) > 0 else ''}{metrics.get('overall_wpm_delta', 0)} WPM",
            ),
            (
                "Segment WPM (Excl. Pauses)",
                f"{metrics.get('speaking_wpm_a', metrics['wpm_a'])} WPM",
                f"{metrics.get('speaking_wpm_b', metrics['wpm_b'])} WPM",
                f"{'+' if metrics.get('speaking_wpm_delta', metrics['wpm_delta']) > 0 else ''}{metrics.get('speaking_wpm_delta', metrics['wpm_delta'])} WPM",
            ),
            (
                "Pauses Count",
                str(metrics["pauses_a"]),
                str(metrics["pauses_b"]),
                f"{'+' if metrics['pauses_delta'] > 0 else ''}{metrics['pauses_delta']}",
            ),
            (
                "Overall Similarity",
                "-",
                "-",
                f"{int(metrics['overall_similarity'] * 100)}%",
            ),
        ]

        for r_idx, (m_name, val_a, val_b, delta) in enumerate(rows, start=1):
            lbl_name = QLabel(m_name)
            lbl_name.setStyleSheet("font-weight: 600; color: #d0d0e0;")

            lbl_a = QLabel(val_a)
            lbl_b = QLabel(val_b)
            lbl_delta = QLabel(delta)
            lbl_delta.setStyleSheet("color: #4daafc; font-weight: 600;")

            self.metrics_layout.addWidget(lbl_name, r_idx, 0)
            self.metrics_layout.addWidget(lbl_a, r_idx, 1)
            self.metrics_layout.addWidget(lbl_b, r_idx, 2)
            self.metrics_layout.addWidget(lbl_delta, r_idx, 3)

        # Clear diff pairs
        while self.diff_layout.count() > 1:
            child = self.diff_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Render aligned pairs side by side
        for pair in aligned_pairs:
            row_frame = QFrame()
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            status = pair["status"]
            style = DIFF_STYLES.get(status, DIFF_STYLES["moderate"])

            # Left Card: Item A
            card_a = self._create_segment_card(pair["item_a"], style, "A")
            # Right Card: Item B
            card_b = self._create_segment_card(pair["item_b"], style, "B")

            row_layout.addWidget(card_a, 1)
            row_layout.addWidget(card_b, 1)
            self.diff_layout.insertWidget(self.diff_layout.count() - 1, row_frame)

    def _create_segment_card(self, item, style, col_tag):
        card = QFrame()
        card.setStyleSheet(style)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        if not item:
            lbl_none = QLabel("(No corresponding segment in this run)")
            lbl_none.setStyleSheet("color: #606070; font-style: italic;")
            layout.addWidget(lbl_none)
            return card

        start = item.get("start", 0.0)
        end = item.get("end", 0.0)
        dur = item.get("duration", 0.0)
        wpm = item.get("wpm", 0.0)

        mins = int(start) // 60
        secs = int(start) % 60
        time_str = f"{mins:02d}:{secs:02d}"

        lbl_header = QLabel(f"[{col_tag}] {time_str} ({dur}s, {wpm} WPM)")
        lbl_header.setStyleSheet("color: #a0a0b8; font-size: 11px; font-weight: 600;")

        lbl_text = QLabel(item.get("text", ""))
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet("color: #ffffff; font-size: 13px;")

        layout.addWidget(lbl_header)
        layout.addWidget(lbl_text)
        return card
