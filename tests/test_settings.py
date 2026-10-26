import json

from tasjeel.config.settings import SettingsManager


def _manager(tmp_path, monkeypatch, user_config=None):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    if user_config is not None:
        config_dir = tmp_path / "Tasjeel" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "config.json").write_text(json.dumps(user_config), encoding="utf-8")
    return SettingsManager()


def test_defaults_target_low_power_cpu(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    assert manager.get("TRANSCRIPTION_PROVIDER") == "Whisper (Local)"
    assert manager.get("WHISPER_MODEL") == "small.en"
    assert manager.get("WHISPER_DEVICE") == "cpu"
    assert manager.get("WHISPER_COMPUTE_TYPE") == "int8"


def test_legacy_gpu_config_is_migrated(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch, {
        "WHISPER_MODEL": "models--ctranslate2-4you--distil-whisper-large-v3-ct2-float32",
        "WHISPER_DEVICE": "cuda",
        "SESSION_AUTO_SAVE": False,
    })
    assert manager.get("WHISPER_MODEL") == "small.en"
    assert manager.get("WHISPER_DEVICE") == "cpu"
    assert manager.get_bool("SESSION_AUTO_SAVE") is False


def test_current_config_is_respected(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch, {
        "WHISPER_MODEL": "base.en",
        "WHISPER_DEVICE": "cpu",
        "WHISPER_COMPUTE_TYPE": "float32",
    })
    assert manager.get("WHISPER_MODEL") == "base.en"
    assert manager.get("WHISPER_COMPUTE_TYPE") == "float32"
