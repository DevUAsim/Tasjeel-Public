import base64
import os
from typing import Optional

import google.generativeai as genai
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from google.api_core import exceptions
from PyQt6.QtWidgets import QApplication

from tasjeel.config import settings as config
from tasjeel.ui import dialogs

SALT_SIZE = 16
KEY_SIZE = 32
DEFAULT_PASSWORD_PROMPT = "Enter password:"
DEFAULT_TITLE_PROMPT = "Password Required"

def generate_salt(size: int = SALT_SIZE) -> bytes:
    return os.urandom(size)

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=config.PBKDF2_ITERATIONS,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def _prompt_for_password(
    text_prompt: str = DEFAULT_PASSWORD_PROMPT, title_prompt: str = DEFAULT_TITLE_PROMPT
) -> Optional[str]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return dialogs.ask_text(None, title_prompt, text_prompt, password=True, confirm_text="Unlock")

def _prompt_for_new_password_and_confirm() -> Optional[str]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    while True:
        password = dialogs.ask_text(None, "Protect your API key",
                                    "Create a password to encrypt the key on this PC.", password=True)
        if not password:
            return None
        confirm_password = dialogs.ask_text(None, "Confirm password", "Type the same password again.",
                                            password=True, confirm_text="Save")
        if not confirm_password:
            return None
        if password == confirm_password:
            return password
        dialogs.inform(None, "Passwords do not match", "Please try again.", "error")

def _encrypt_and_save_api_key(api_key: str, password: str) -> bool:
    try:
        salt = generate_salt()
        derived_key = _derive_key(password, salt)
        fernet = Fernet(derived_key)
        encrypted_api_key = fernet.encrypt(api_key.encode())
        with open(config.SALT_FILE, "wb") as sf:
            sf.write(salt)
        with open(config.ENCRYPTED_API_KEY_FILE, "wb") as ef:
            ef.write(encrypted_api_key)
        print("API Key encrypted and saved.")
        return True
    except Exception as e:
        print(f"Error encrypting/saving API key: {e}")
        return False

def _load_and_decrypt_api_key(prompt_for_password: bool = True) -> Optional[str]:
    if not (
        os.path.exists(config.SALT_FILE)
        and os.path.exists(config.ENCRYPTED_API_KEY_FILE)
    ):
        return None
    if not prompt_for_password:
        return None
    password = _prompt_for_password(
        text_prompt="Enter password to decrypt API key:", title_prompt="Decrypt API Key"
    )
    if not password:
        print("Password not provided for decryption.")
        return None
    try:
        with open(config.SALT_FILE, "rb") as sf:
            salt = sf.read()
        with open(config.ENCRYPTED_API_KEY_FILE, "rb") as ef:
            encrypted_api_key = ef.read()
        derived_key = _derive_key(password, salt)
        fernet = Fernet(derived_key)
        decrypted_api_key = fernet.decrypt(encrypted_api_key).decode()
        print("API Key decrypted successfully.")
        return decrypted_api_key
    except InvalidToken:
        print("Failed to decrypt API key. Incorrect password or corrupted data.")
        dialogs.inform(None, "Could not unlock the key", "The password is incorrect or the key file is damaged.", "error")
        return None
    except Exception as e:
        print(f"Error loading/decrypting API key: {e}")
        return None

def save_api_key(api_key: str) -> bool:
    password = _prompt_for_new_password_and_confirm()
    if password:
        return _encrypt_and_save_api_key(api_key, password)
    return False


def get_api_key(prompt_user: bool = True) -> Optional[str]:
    api_key = _load_and_decrypt_api_key(prompt_for_password=prompt_user)
    if api_key:
        return api_key
    env_api_key = os.environ.get("GOOGLE_API_KEY")
    if env_api_key:
        if prompt_user:
            print("API key found in environment variable.")
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            if dialogs.confirm(None, "Save API key?",
                               "A key was found in GOOGLE_API_KEY. Save it encrypted for future use?",
                               confirm_text="Save"):
                password = _prompt_for_new_password_and_confirm()
                if password:
                    _encrypt_and_save_api_key(env_api_key, password)
        return env_api_key
    if not prompt_user:
        return None
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    entered_key = dialogs.ask_text(None, "Gemini API key", "Paste your Google Gemini API key, or cancel to use local Whisper only.",
                                   password=True)
    if entered_key:
        print("API key entered by user.")
        if dialogs.confirm(None, "Save API key?", "Save this key encrypted for future use?", confirm_text="Save"):
            password = _prompt_for_new_password_and_confirm()
            if password:
                _encrypt_and_save_api_key(entered_key, password)
        return entered_key
    return None


def validate_api_key(api_key: str) -> bool | str:
    try:
        genai.configure(api_key=api_key)
        list(genai.list_models())
        return True
    except exceptions.PermissionDenied:
        return "Invalid API Key. Please check if the key is correct and has the necessary permissions."
    except Exception as e:
        return f"An error occurred during key validation: {e}"
