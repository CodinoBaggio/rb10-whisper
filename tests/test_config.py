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
