import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from src.config import ConfigManager


def test_get_whisper_url_returns_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        url = ConfigManager.get_whisper_url()
    assert url == "http://localhost:8000/v1"


def test_get_whisper_url_returns_custom():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={"whisper_url": "http://192.168.1.10:8000/v1"}):
        url = ConfigManager.get_whisper_url()
    assert url == "http://192.168.1.10:8000/v1"


def test_get_mic_device_returns_none_by_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        device = ConfigManager.get_mic_device()
    assert device is None


def test_get_mic_device_returns_saved_name():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={"mic_device": "Microphone (Blue Yeti)"}):
        device = ConfigManager.get_mic_device()
    assert device == "Microphone (Blue Yeti)"


def test_set_mic_device_saves_name(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_mic_device("Microphone (Blue Yeti)")
    ConfigManager._config_cache = None
    assert ConfigManager.get_mic_device() == "Microphone (Blue Yeti)"


def test_set_mic_device_saves_none(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_mic_device(None)
    ConfigManager._config_cache = None
    assert ConfigManager.get_mic_device() is None


def test_set_whisper_url_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_whisper_url("http://192.168.1.100:8001/v1")
    ConfigManager._config_cache = None
    assert ConfigManager.get_whisper_url() == "http://192.168.1.100:8001/v1"


def test_set_whisper_model_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_whisper_model("openai/whisper-large-v3")
    ConfigManager._config_cache = None
    assert ConfigManager.get_whisper_model() == "openai/whisper-large-v3"


def test_parse_hotkey_returns_modifier_and_key():
    modifier, key = ConfigManager.parse_hotkey("ctrl+x")
    assert modifier == "ctrl"
    assert key == "x"


def test_parse_hotkey_handles_multichar_key():
    modifier, key = ConfigManager.parse_hotkey("alt+space")
    assert modifier == "alt"
    assert key == "space"


def test_parse_hotkey_returns_empty_for_old_format():
    modifier, key = ConfigManager.parse_hotkey("alt")
    assert modifier == ""
    assert key == ""


def test_get_hotkey_toggle_returns_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        toggle = ConfigManager.get_hotkey_toggle()
    assert toggle == "alt+z"


def test_set_hotkey_toggle_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_hotkey_toggle("ctrl+q")
    ConfigManager._config_cache = None
    assert ConfigManager.get_hotkey_toggle() == "ctrl+q"


def test_get_ai_mode_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        assert ConfigManager.get_ai_mode() == "off"


def test_set_ai_mode_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_ai_mode("refine")
    ConfigManager._config_cache = None
    assert ConfigManager.get_ai_mode() == "refine"


def test_get_ollama_url_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        assert ConfigManager.get_ollama_url() == "http://localhost:11434"


def test_set_ollama_url_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_ollama_url("http://localhost:11435")
    ConfigManager._config_cache = None
    assert ConfigManager.get_ollama_url() == "http://localhost:11435"


def test_get_ollama_model_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        assert ConfigManager.get_ollama_model() == "qwen2.5:7b"


def test_set_ollama_model_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_ollama_model("gemma3:4b")
    ConfigManager._config_cache = None
    assert ConfigManager.get_ollama_model() == "gemma3:4b"

