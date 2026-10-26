import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from tasjeel.config.settings import settings_manager
from .api_manager import APIManager

PREVIEW_TEXT_LENGTH = 300
MIN_AI_NAME_LENGTH = 3
MAX_AI_NAME_LENGTH = 60
FALLBACK_NAME_WORDS = 5
DEFAULT_MAX_RECENT_SESSIONS = 50
SESSION_FILE_EXTENSION = ".json"
DEFAULT_ENCODING = "utf-8"
JSON_INDENT_SIZE = 2

class SessionManager:
    def __init__(self, api_manager: APIManager):
        self.sessions_directory = settings_manager.SESSIONS_DIRECTORY
        self.current_session_id: Optional[str] = None
        self.api_manager = api_manager
        self.ensure_sessions_directory()

    def ensure_sessions_directory(self) -> None:
        try:
            Path(self.sessions_directory).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating sessions directory: {e}")

    def generate_session_id(self) -> str:
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def _generate_fallback_name(self, transcription_text: str) -> str:
        if not transcription_text.strip():
            return f"Empty Session {datetime.datetime.now().strftime('%H:%M')}"
        preview = " ".join(transcription_text.strip().split()[:FALLBACK_NAME_WORDS])
        return preview.title()

    def generate_ai_session_name(
        self, transcription_text: str, metadata: Dict[str, Any]
    ) -> str:
        if not settings_manager.get_bool("AI_GENERATE_SESSION_NAMES"):
            return self._generate_fallback_name(transcription_text)
        try:
            language = metadata.get("language", "English")
            preview = transcription_text[:PREVIEW_TEXT_LENGTH].strip()
            prompt = (
                "Based on the following transcription excerpt, generate a concise, descriptive title (3-6 words).\n"
                f"The text is in {language}.\n"
                f'Excerpt: "{preview}"\n\n'
                "Rules:\n- Be specific and descriptive.\n- Avoid generic words like 'Session' or 'Recording'.\n"
                "- Use title case.\n\nTitle:"
            )
            model = self.api_manager.get_model()
            if not model:
                raise ConnectionError("API model not available for naming.")
            response = model.generate_content(prompt)
            if response and response.text:
                ai_name = response.text.strip().strip("\"'")
                if MIN_AI_NAME_LENGTH < len(ai_name) <= MAX_AI_NAME_LENGTH:
                    return ai_name
        except Exception as e:
            print(f"AI naming failed, using fallback. Error: {e}")
        return self._generate_fallback_name(transcription_text)

    def save_session(
        self,
        transcription_text: str,
        metadata: Dict[str, Any],
        session_id: Optional[str] = None,
        session_name: Optional[str] = None,
    ) -> Optional[str]:
        try:
            session_id = session_id or self.generate_session_id()
            if not session_name:
                session_name = self.generate_ai_session_name(
                    transcription_text, metadata
                )
            session_data = {
                "id": session_id,
                "name": session_name,
                "timestamp": datetime.datetime.now().isoformat(),
                "transcription": transcription_text,
                "metadata": metadata,
            }
            session_file = Path(self.sessions_directory) / f"{session_id}{SESSION_FILE_EXTENSION}"
            with open(session_file, "w", encoding=DEFAULT_ENCODING) as f:
                json.dump(session_data, f, indent=JSON_INDENT_SIZE, ensure_ascii=False)
            self.current_session_id = session_id
            return session_id
        except Exception as e:
            print(f"Error saving session: {e}")
            return None

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session_file = Path(self.sessions_directory) / f"{session_id}{SESSION_FILE_EXTENSION}"
        if not session_file.exists():
            return None
        try:
            with open(session_file, "r", encoding=DEFAULT_ENCODING) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        session_file = Path(self.sessions_directory) / f"{session_id}{SESSION_FILE_EXTENSION}"
        try:
            if session_file.exists():
                session_file.unlink()
                return True
            return False
        except OSError as e:
            print(f"Error deleting session {session_id}: {e}")
            return False

    def get_recent_sessions(self) -> List[Dict[str, Any]]:
        sessions_path = Path(self.sessions_directory)
        if not sessions_path.exists():
            return []
        session_files = []
        try:
            for f in sessions_path.glob(f"*{SESSION_FILE_EXTENSION}"):
                mtime = f.stat().st_mtime
                session_files.append((f, mtime))
        except OSError as e:
            print(f"Error reading sessions directory: {e}")
            return []
        session_files.sort(key=lambda x: x[1], reverse=True)
        recent_sessions = []
        limit = settings_manager.get_int("MAX_RECENT_SESSIONS", DEFAULT_MAX_RECENT_SESSIONS)
        for f_path, _ in session_files[:limit]:
            session_data = self.load_session(
                f_path.stem
            )
            if session_data:
                recent_sessions.append(session_data)
        return recent_sessions

    def update_sessions_directory(self, new_directory: str):
        self.sessions_directory = new_directory
        self.ensure_sessions_directory()

    def is_unsaved(self, session_id: Optional[str], current_text: str) -> bool:
        if not session_id:
            return bool(current_text.strip())
        saved_session = self.load_session(session_id)
        if not saved_session:
            return bool(current_text.strip())
        return current_text != saved_session.get("transcription", "")
