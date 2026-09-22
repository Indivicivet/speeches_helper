import os
import shutil
import tempfile
import unittest
from pathlib import Path
from src.core.session_manager import REPO_ROOT, SessionManager


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.manager = SessionManager(sessions_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load_session(self):
        session_id = "session_20260920_120000"
        saved = self.manager.save_initial_session(
            session_id=session_id,
            global_duration_seconds=125.4,
            phone_timer_used=True,
            phone_timer_duration=180,
            phone_timer_start_time=10.5,
            peek_events=[{"timer": "phone", "time": 45.0}],
        )
        self.assertEqual(saved["session_id"], session_id)
        self.assertEqual(saved["global_duration_seconds"], 125.4)
        self.assertTrue(saved["phone_timer"]["used"])

        # Load back
        loaded = self.manager.load_session(session_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["session_id"], session_id)
        self.assertEqual(loaded["status"], "recorded")

    def test_update_transcription_and_profile(self):
        session_id = "session_20260920_130000"
        self.manager.save_initial_session(session_id, 60.0)

        transcription = {
            "model": "medium.en",
            "segments": [{"start": 0.0, "end": 5.0, "text": "Hello world"}],
        }
        profile = {
            "effective_duration_seconds": 5.0,
            "total_words": 2,
            "speaking_pace_wpm": 24.0,
        }

        updated = self.manager.update_transcription_and_profile(
            session_id, transcription, profile
        )
        self.assertEqual(updated["status"], "processed")
        self.assertEqual(updated["transcription"]["model"], "medium.en")
        self.assertEqual(updated["profile"]["total_words"], 2)

    def test_list_sessions(self):
        self.manager.save_initial_session("session_20260920_100000", 30.0)
        self.manager.save_initial_session("session_20260920_110000", 45.0)

        sessions = self.manager.list_sessions()
        self.assertEqual(len(sessions), 2)
        # Should be reverse chronological
        self.assertEqual(sessions[0]["session_id"], "session_20260920_110000")
        self.assertEqual(sessions[1]["session_id"], "session_20260920_100000")

    def test_sessions_dir_relative_to_repo_root(self):
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            manager_default = SessionManager()
            self.assertEqual(
                manager_default.sessions_dir, (REPO_ROOT / "sessions").resolve()
            )

            manager_relative = SessionManager("sessions")
            self.assertEqual(
                manager_relative.sessions_dir, (REPO_ROOT / "sessions").resolve()
            )
        finally:
            os.chdir(orig_cwd)


if __name__ == "__main__":
    unittest.main()
