import json
import os
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class SessionManager:
    """Manages reading, writing, and listing speech session files."""

    def __init__(self, sessions_dir="sessions"):
        sessions_path = Path(sessions_dir)
        self.sessions_dir = (
            sessions_path
            if sessions_path.is_absolute()
            else (REPO_ROOT / sessions_path).resolve()
        )
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def generate_session_id(self):
        return datetime.now().strftime("session_%Y%m%d_%H%M%S")

    def get_audio_path(self, session_id):
        return self.sessions_dir / f"{session_id}.mp3"

    def get_json_path(self, session_id):
        return self.sessions_dir / f"{session_id}.json"

    def save_initial_session(
        self,
        session_id,
        global_duration_seconds,
        phone_timer_used=False,
        phone_timer_duration=180,
        phone_timer_start_time=None,
        phone_timer_starts=None,
        peek_events=None,
        has_initial_audio=None,
    ):
        """Immediately persists initial session metadata before transcription."""
        payload = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "status": "recorded",
            "audio_file": f"{session_id}.mp3",
            "global_duration_seconds": round(global_duration_seconds, 2),
            "phone_timer": {
                "used": phone_timer_used,
                "duration_seconds": phone_timer_duration,
                "start_time_seconds": (
                    round(phone_timer_start_time, 2)
                    if phone_timer_start_time is not None
                    else None
                ),
                "starts": phone_timer_starts or [],
            },
            "peek_events": peek_events or [],
            "transcription": None,
            "profile": None,
        }
        if has_initial_audio is not None:
            payload["has_initial_audio"] = bool(has_initial_audio)
        json_path = self.get_json_path(session_id)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return payload

    def update_transcription_and_profile(
        self, session_id, transcription_data, profile_data, has_initial_audio=None
    ):
        """Updates an existing session record with transcription and profile analysis."""
        json_path = self.get_json_path(session_id)
        if not json_path.exists():
            data = {"session_id": session_id}
        else:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        data["status"] = "processed"
        data["transcription"] = transcription_data
        data["profile"] = profile_data
        if has_initial_audio is not None:
            data["has_initial_audio"] = bool(has_initial_audio)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data

    def load_session(self, session_id):
        json_path = self.get_json_path(session_id)
        if not json_path.exists():
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self):
        """Returns a list of all session metadata dictionaries, newest first."""
        sessions = []
        for json_file in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    audio_path = self.sessions_dir / data.get(
                        "audio_file", f"{data.get('session_id')}.mp3"
                    )
                    data["audio_exists"] = audio_path.exists()
                    data["audio_path"] = str(audio_path)
                    sessions.append(data)
            except Exception:
                continue
        return sessions
