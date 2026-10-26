import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

ENCRYPTED_API_KEY_FILE = "api_key.enc"
SALT_FILE = "salt.bin"
PBKDF2_ITERATIONS = 100000
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_DURATION = 30
DEFAULT_MAX_RETRIES = 3
CONFIG_FILE_NAME = "config.json"
SESSIONS_FOLDER_NAME = "sessions"

SUPPORTED_LANGUAGES: List[str] = [
    "English", "Urdu", "Roman Urdu", "Arabic", "Persian"
]
EXPORT_FORMATS: List[Tuple[str, str]] = [
    ("Plain Text (.txt)", "txt"),
    ("Microsoft Word (.docx)", "docx"),
    ("PDF Document (.pdf)", "pdf"),
    ("JSON Format (.json)", "json"),
    ("HTML Document (.html)", "html")
]

class SettingsManager:
    def __init__(self):
        if os.name == 'nt':
            app_data = os.getenv('APPDATA')
            if app_data:
                self._base_directory = Path(app_data) / "Tasjeel"
            else:
                self._base_directory = Path(os.path.expanduser("~")) / "Tasjeel_Data"
        else:
            self._base_directory = Path(os.path.expanduser("~")) / ".tasjeel"
            
        self._config_directory = self._base_directory / "config"
        self._config_file = self._config_directory / CONFIG_FILE_NAME
        self._defaults: Dict[str, Any] = {
            'GEMINI_MODEL_NAME': "gemini-flash-latest",
            'SUPPRESS_GEMINI_PROMPT': False,
            'SAMPLE_RATE': DEFAULT_SAMPLE_RATE,
            'CHUNK_DURATION_SECONDS': DEFAULT_CHUNK_DURATION,
            'MAX_RETRIES_STANDARD': DEFAULT_MAX_RETRIES,
            'SESSIONS_DIRECTORY': str(self._base_directory / SESSIONS_FOLDER_NAME),
            'SESSION_AUTO_SAVE': True,
            'AI_GENERATE_SESSION_NAMES': True,
            'AUDIO_INPUT_DEVICE_ID': None,
            'TRANSCRIPTION_PROVIDER': "Whisper (Local)",
            'WHISPER_MODEL': "small.en",
            'WHISPER_DEVICE': "cpu",
            'WHISPER_COMPUTE_TYPE': "int8",
            'LAST_TRANSCRIPTION_LANGUAGE': "English",
            'LAST_TRANSCRIPTION_SPEAKERS': "1 Speaker",
            'LAST_TRANSCRIPTION_NOISE': "Low",
            'LAST_CONTEXT_NOTES': "",
        }
        self._settings = self._defaults.copy()
        self.load()

    def _ensure_dirs_exist(self):
        try:
            self._config_directory.mkdir(parents=True, exist_ok=True)
            sessions_dir = Path(self.get('SESSIONS_DIRECTORY'))
            sessions_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Error creating necessary directories: {e}")

    def load(self):
        self._ensure_dirs_exist()
        if not self._config_file.exists():
            return

        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            if 'WHISPER_COMPUTE_TYPE' not in user_config:
                for key in ('TRANSCRIPTION_PROVIDER', 'WHISPER_MODEL', 'WHISPER_DEVICE'):
                    user_config.pop(key, None)
            self._settings.update(user_config)
            print("User settings loaded.")
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading user config file '{self._config_file}': {e}. Using defaults.")
            self._settings = self._defaults.copy()

    def save(self) -> bool:
        self._ensure_dirs_exist()
        
        if not self._config_directory.exists():
            print(f"Config directory does not exist: {self._config_directory}")
            return False
            
        try:
            json_data = json.dumps(self._settings, indent=2, ensure_ascii=False)
            temp_file = self._config_file.parent / (self._config_file.name + '.tmp')
            
            with open(str(temp_file), 'w', encoding='utf-8') as f:
                f.write(json_data)
                f.flush()
                os.fsync(f.fileno())
            
            if self._config_file.exists():
                self._config_file.unlink()
            temp_file.rename(self._config_file)
            
            print("User settings saved.")
            return True
        except Exception as e:
            print(f"Error saving user config file '{self._config_file}': {e}")
            try:
                if 'temp_file' in locals() and Path(temp_file).exists():
                    Path(temp_file).unlink()
            except:
                pass
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        return bool(self.get(key, default))

    def set(self, key: str, value: Any):
        self._settings[key] = value

    def get_all_settings(self) -> Dict[str, Any]:
        return self._settings.copy()

    def update_sessions_directory(self, new_path: str):
        self.set('SESSIONS_DIRECTORY', new_path)
        self._ensure_dirs_exist()
        
    @property
    def SESSIONS_DIRECTORY(self) -> str:
        return str(self.get('SESSIONS_DIRECTORY'))

settings_manager = SettingsManager()
