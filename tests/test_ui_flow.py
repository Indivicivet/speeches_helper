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
        for f in [
            "test_session_ui_flow.json",
            "test_compare_1.json",
            "test_compare_2.json",
        ]:
            path = self.window.session_manager.sessions_dir / f
            if path.exists():
                path.unlink()
        self.window.close()
        self.window.deleteLater()
        self.window = None
        app.processEvents()

    def test_practice_timers_and_peeks(self):
        practice = self.window.practice_view

        # Timers must be hidden by default
        self.assertTrue(practice.chk_hide_global.isChecked())
        self.assertTrue(practice.chk_hide_phone.isChecked())
        self.assertEqual(practice.lbl_global_timer.text(), "••:••")
        self.assertEqual(practice.lbl_phone_timer.text(), "••:••")

        # Test unchecking shows real time
        practice.chk_hide_global.setChecked(False)
        self.assertEqual(practice.lbl_global_timer.text(), "00:00")
        practice.chk_hide_global.setChecked(True)
        self.assertEqual(practice.lbl_global_timer.text(), "••:••")

        # Test peek global
        practice._on_peek_global_press()
        practice._update_display()
        self.assertNotEqual(practice.lbl_global_timer.text(), "••:••")
        practice._on_peek_global_release()
        practice._update_display()
        self.assertEqual(practice.lbl_global_timer.text(), "••:••")

        # Test peek phone
        practice._on_peek_phone_press()
        practice._update_display()
        self.assertNotEqual(practice.lbl_phone_timer.text(), "••:••")
        practice._on_peek_phone_release()
        practice._update_display()
        self.assertEqual(practice.lbl_phone_timer.text(), "••:••")

        # Test start phone timer visual feedback
        practice.start_phone_timer()
        self.assertEqual(practice.btn_start_phone.text(), "Restart Phone Timer (T)")
        self.assertIn("RUNNING", practice.lbl_phone_status.text())
        self.assertEqual(len(practice.phone_timer_starts), 1)

        # Test stopping timer BEFORE alarm triggers
        practice.stop_timer_or_alarm()
        self.assertFalse(practice.phone_timer_active)
        self.assertEqual(practice.btn_start_phone.text(), "Start Phone Timer (T)")
        self.assertEqual(practice.lbl_phone_status.text(), "○ Timer stopped")

        # Test starting again adds second start event
        practice.start_phone_timer()
        self.assertEqual(len(practice.phone_timer_starts), 2)

    def test_phone_timer_during_active_speech(self):
        import time

        practice = self.window.practice_view
        practice.start_speech()
        self.assertTrue(practice.is_speaking)

        # Start phone timer while speech is actively running
        practice.start_phone_timer()
        self.assertTrue(practice.phone_timer_active)
        self.assertEqual(practice.btn_start_phone.text(), "Restart Phone Timer (T)")
        self.assertIn("RUNNING", practice.lbl_phone_status.text())

        # Simulate time passing and ticking
        time.sleep(0.15)
        practice._on_tick()
        self.assertLess(
            practice.phone_remaining_seconds, practice.phone_duration_seconds
        )

        # Stop speech and verify metadata
        metadata = None

        def record_meta(meta):
            nonlocal metadata
            metadata = meta

        practice.speech_stopped.connect(record_meta)
        practice.stop_speech()

        self.assertIsNotNone(metadata)
        self.assertTrue(metadata["phone_timer_used"])
        self.assertGreater(len(metadata["phone_timer_starts"]), 0)

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

        # Check that tab did NOT auto-switch (stays on current tab, e.g. 0)
        self.assertEqual(self.window.tabs.currentIndex(), 0)

        # Explicitly select session in report view to verify profile data population
        self.window.report_view.select_session(session_id)

        # Check KPI values
        report = self.window.report_view
        self.assertEqual(report.card_total_time.value_label.text(), "00:12")
        self.assertEqual(report.card_effective_time.value_label.text(), "00:09")
        self.assertEqual(report.card_words.value_label.text(), "15")
        self.assertIn("WPM", report.card_wpm.value_label.text())
        self.assertIsNotNone(report.card_phone_timer.value_label.text())

    def test_transcription_queue_overlapping_runs(self):
        # Enqueue multiple speech stop events without waiting
        self.window.transcription_queue.clear()
        self.window.current_transcription_job = None

        meta1 = {
            "global_duration_seconds": 10.0,
            "phone_timer_used": False,
            "phone_timer_duration": 180,
            "phone_timer_start_time": None,
            "peek_events": [],
            "model_name": "medium.en",
            "pause_threshold": 1.5,
        }
        meta2 = {
            "global_duration_seconds": 15.0,
            "phone_timer_used": False,
            "phone_timer_duration": 180,
            "phone_timer_start_time": None,
            "peek_events": [],
            "model_name": "medium.en",
            "pause_threshold": 1.5,
        }

        # Simulate job 1 already in progress
        self.window.current_transcription_job = {"session_id": "job1"}

        # Simulate speech stopped for run 2
        self.window.current_session_id = "job2"
        self.window._on_speech_stopped(meta1)

        # Simulate speech stopped for run 3
        self.window.current_session_id = "job3"
        self.window._on_speech_stopped(meta2)

        # Both jobs should be safely queued
        self.assertEqual(len(self.window.transcription_queue), 2)
        self.assertEqual(self.window.transcription_queue[0]["session_id"], "job2")
        self.assertEqual(self.window.transcription_queue[1]["session_id"], "job3")

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

    def test_audio_warning_banners(self):
        practice = self.window.practice_view
        self.assertTrue(practice.audio_warning_banner.isHidden())
        practice.show_audio_warning()
        self.assertFalse(practice.audio_warning_banner.isHidden())
        practice.clear_audio_warning()
        self.assertTrue(practice.audio_warning_banner.isHidden())

        report = self.window.report_view
        sess_no_audio = {
            "session_id": "test_no_audio",
            "global_duration_seconds": 10.0,
            "has_initial_audio": False,
            "profile": {},
        }
        report.display_session(sess_no_audio)
        self.assertFalse(report.warning_banner.isHidden())

        sess_with_audio = {
            "session_id": "test_with_audio",
            "global_duration_seconds": 10.0,
            "has_initial_audio": True,
            "profile": {},
        }
        report.display_session(sess_with_audio)
        self.assertTrue(report.warning_banner.isHidden())


if __name__ == "__main__":
    unittest.main()
