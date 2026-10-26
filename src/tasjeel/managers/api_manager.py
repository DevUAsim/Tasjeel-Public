from typing import Optional

import google.generativeai as genai

from tasjeel.config.settings import settings_manager
from tasjeel.ui import dialogs
from tasjeel.utils.key_manager import get_api_key

class APIManager:
    def __init__(self):
        self.api_key: Optional[str] = None
        self.model: Optional[genai.GenerativeModel] = None

    def initialize_api(self) -> bool:
        suppressed = settings_manager.get_bool("SUPPRESS_GEMINI_PROMPT") or "gemini" not in (
            settings_manager.get("TRANSCRIPTION_PROVIDER") or "").lower()
        self.api_key = get_api_key(prompt_user=not suppressed)
        
        if not self.api_key:
            if not suppressed:
                if dialogs.confirm(
                    None,
                    "Stop asking for a Gemini key?",
                    "Tasjeel will use local Whisper transcription. You can add a key later in Settings.",
                    confirm_text="Stop asking",
                    cancel_text="Ask next time",
                ):
                    settings_manager.set("SUPPRESS_GEMINI_PROMPT", True)
                    settings_manager.save()
            return False

        try:
            genai.configure(api_key=self.api_key)
            model_name = settings_manager.get("GEMINI_MODEL_NAME")
            self.model = genai.GenerativeModel(model_name)
            print(
                f"Google Generative AI configured successfully with model: {model_name}"
            )
            return True
        except Exception as e:
            print(f"Failed to configure Gemini API: {e}. Please check your API key.")
            return False

    def get_model(self) -> Optional[genai.GenerativeModel]:
        return self.model

    def get_api_key(self) -> Optional[str]:
        return self.api_key

    def is_initialized(self) -> bool:
        return self.api_key is not None and self.model is not None
