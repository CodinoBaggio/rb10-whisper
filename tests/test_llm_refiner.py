import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock
import pytest
from src.config import ConfigManager
from src.llm_refiner import LLMRefiner


def test_refine_returns_original_text_when_mode_is_off():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'get_ai_mode', return_value="off"):
        refiner = LLMRefiner()
        result = refiner.refine("こんにちは えーテストです")
        assert result == "こんにちは えーテストです"


def test_refine_calls_ollama_for_refine_mode():
    ConfigManager._config_cache = None
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "こんにちはテストです。"}
    mock_response.status_code = 200

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('requests.post', return_value=mock_response) as mock_post:
        
        refiner = LLMRefiner()
        result = refiner.refine("こんにちは えーテストです")
        assert result == "こんにちはテストです。"
        assert mock_post.called


def test_refine_calls_ollama_for_business_mode():
    ConfigManager._config_cache = None
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "お世話になっております。テストの件、承知いたしました。"}
    mock_response.status_code = 200

    with patch.object(ConfigManager, 'get_ai_mode', return_value="business"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('requests.post', return_value=mock_response) as mock_post:
        
        refiner = LLMRefiner()
        result = refiner.refine("テストの件了解")
        assert result == "お世話になっております。テストの件、承知いたしました。"


def test_refine_fallback_to_original_text_on_error():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch('requests.post', side_effect=Exception("Connection refused")):
        
        refiner = LLMRefiner()
        result = refiner.refine("テストテキスト")
        assert result == "テストテキスト"


def test_fetch_available_models():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "qwen2.5:7b"},
            {"name": "gemma3:4b"}
        ]
    }
    mock_response.status_code = 200

    with patch('requests.get', return_value=mock_response):
        models = LLMRefiner.fetch_available_models("http://localhost:11434")
        assert "qwen2.5:7b" in models
        assert "gemma3:4b" in models
