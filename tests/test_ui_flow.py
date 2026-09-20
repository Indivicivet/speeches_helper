import os
import sys
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from src.core.session_manager import SessionManager
from src.ui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestUIFlow(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()

    def tearDown(self):
        self.window.close()
        for f in [
            "test_session_ui_flow.json",
            "test_compare_1.json",
            "test_compare_2.json",
        ]:
            path = self.window.session_manager.sessions_dir / f
            if path.exists():
                path.unlink()

    def test_practice_timers_and_peeks(self):
        practice = self.window.practice_view

        # Test hidden state toggle
        practice.chk_hide_global.setChecked(True)
        practice._update_display()
        self.assertEqual(practice.lbl_global_timer.text(), "••:••")

        # Test peek global
        practice._on_peek_global_press()
        practice._update_display()
        self.assertNotEqual(practice.lbl_global_timer.text(), "••:••")
        practice._on_peek_global_release()
        practice._update_display()
        self.assertEqual(practice.lbl_global_timer.text(), "••:••")

        # Test phone timer
        practice.chk_hide_phone.setChecked(True)
        practice._update_display()
        self.assertEqual(practice.lbl_phone_timer.text(), "••:••")

        practice._on_peek_phone_press()
        practice._update_display()
        self.assertNotEqual(practice.lbl_phone_timer.text(), "••:••")
        practice._on_peek_phone_release()
        practice._update_display()
        self.assertEqual(practice.lbl_phone_timer.text(), "••:••")

    def test_transcription_finished_populates_report(self):
        session_id = "test_session_ui_flow"
        mock_trans = {
            "model": "medium.en",
            "segments": [
                {
                    "id": 0,
                    "start": 1.0,
                    "end": 4.0,
                    "text": "Hello world and welcome to speech practice.",
                },
                {
                    "id": 1,
                    "start": 6.5,
                    "end": 9.0,
                    "text": "This is the second segment after a pause.",
                },
            ],
        }

        # Save initial session
        self.window.session_manager.save_initial_session(session_id, 12.0)

        # Trigger transcription completion callback
        self.window._on_transcription_finished(
            session_id=session_id,
            trans_result=mock_trans,
            global_duration=12.0,
            pause_threshold=1.5,
        )

        # Check that Report tab is selected (index 1)
        self.assertEqual(self.window.tabs.currentIndex(), 1)

        # Check KPI values
        report = self.window.report_view
        self.assertEqual(report.card_total_time.value_label.text(), "00:12")
        self.assertEqual(report.card_effective_time.value_label.text(), "00:09")
        self.assertEqual(report.card_words.value_label.text(), "15")
        self.assertIn("WPM", report.card_wpm.value_label.text())

    def test_compare_view_rendering(self):
        sess1 = "test_compare_1"
        sess2 = "test_compare_2"

        self.window.session_manager.save_initial_session(sess1, 10.0)
        self.window.session_manager.save_initial_session(sess2, 12.0)

        mock1 = {
            "model": "medium.en",
            "segments": [{"id": 0, "start": 0.0, "end": 5.0, "text": "Opening joke"}],
        }
        mock2 = {
            "model": "medium.en",
            "segments": [
                {"id": 0, "start": 0.0, "end": 5.5, "text": "Opening joke altered"}
            ],
        }

        self.window._on_transcription_finished(sess1, mock1, 10.0, 1.5)
        self.window._on_transcription_finished(sess2, mock2, 12.0, 1.5)

        self.window.tabs.setCurrentIndex(2)
        compare = self.window.compare_view
        compare.refresh_session_lists()

        idx1 = compare.combo_a.findData(sess1)
        idx2 = compare.combo_b.findData(sess2)
        if idx1 >= 0:
            compare.combo_a.setCurrentIndex(idx1)
        if idx2 >= 0:
            compare.combo_b.setCurrentIndex(idx2)

        compare.run_comparison()
        # Verify metrics table has been populated
        self.assertGreater(compare.metrics_layout.count(), 4)


if __name__ == "__main__":
    unittest.main()
