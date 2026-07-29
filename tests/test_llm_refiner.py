import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from unittest.mock import patch, MagicMock
import pytest
from src.config import ConfigManager
from src.llm_refiner import LLMRefiner


def _make_mock_response(json_data, status=200):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(json_data).encode("utf-8")
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_resp
    return mock_ctx


def test_refine_returns_original_text_when_mode_is_off():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'get_ai_mode', return_value="off"):
        refiner = LLMRefiner()
        result = refiner.refine("こんにちは えーテストです")
        assert result == "こんにちは えーテストです"


def test_refine_calls_ollama_for_refine_mode():
    ConfigManager._config_cache = None
    mock_ctx = _make_mock_response({"message": {"content": "こんにちはテストです。"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:
        
        refiner = LLMRefiner()
        result = refiner.refine("こんにちは えーテストです")
        assert result == "こんにちはテストです。"
        assert mock_urlopen.called


def test_refine_sends_casual_request_preservation_rules():
    ConfigManager._config_cache = None
    mock_ctx = _make_mock_response({"message": {"content": "このデータ保存しといて"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:

        result = LLMRefiner().refine("このデータ保存しといて")

    request = mock_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    system_prompt = payload["messages"][0]["content"]

    assert result == "このデータ保存しといて"
    assert payload["messages"][1] == {"role": "user", "content": "このデータ保存しといて"}
    assert "このデータ保存しといて" in system_prompt
    assert "このデータを保存しておきます" in system_prompt
    assert "敬語や丁寧な断定に変換しない" in system_prompt

def test_legacy_business_mode_uses_selected_text_for_editing():
    mock_ctx = _make_mock_response({"message": {"content": "お世話になっております。テストの件、承知いたしました。"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="business"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine("丁寧にして", selected_text="テストの件了解")

    assert result == "お世話になっております。テストの件、承知いたしました。"


def test_refine_fallback_to_original_text_on_error():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch('urllib.request.urlopen', side_effect=Exception("Connection refused")):
        
        refiner = LLMRefiner()
        result = refiner.refine("テストテキスト")
        assert result == "テストテキスト"




def test_refine_falls_back_to_transcript_when_llm_output_is_unrelated():
    original = "明日の予定を確認してくれ"
    mock_ctx = _make_mock_response({"message": {"content": "月曜に電話する"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == original


def test_business_mode_without_selection_does_not_call_ollama():
    with patch.object(ConfigManager, 'get_ai_mode', return_value="business"), \
         patch('urllib.request.urlopen') as mock_urlopen:
        result = LLMRefiner().refine("丁寧にして")

    assert result == "丁寧にして"
    mock_urlopen.assert_not_called()


def test_edit_mode_sends_spoken_instruction_and_selected_text():
    mock_ctx = _make_mock_response({"message": {"content": "選択した文を丁寧にした結果"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="edit"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:
        result = LLMRefiner().refine("丁寧にして", selected_text="これは選択中の文です")

    request = mock_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    user_content = payload["messages"][1]["content"]

    assert result == "選択した文を丁寧にした結果"
    assert "<spoken_instruction>" in user_content
    assert "丁寧にして" in user_content
    assert "<selected_text>" in user_content
    assert "これは選択中の文です" in user_content


def test_edit_mode_preserves_selected_text_whitespace_in_request():
    selected_text = "  first line\n"
    mock_ctx = _make_mock_response({"message": {"content": "edited"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="edit"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:
        LLMRefiner().refine("rewrite it", selected_text=selected_text)

    request = mock_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))

    assert "<selected_text>\n  first line\n\n</selected_text>" in payload["messages"][1]["content"]

def test_fetch_available_models():
    mock_ctx = _make_mock_response({
        "models": [
            {"name": "qwen2.5:7b"},
            {"name": "gemma3:4b"}
        ]
    })

    with patch('urllib.request.urlopen', return_value=mock_ctx):
        models = LLMRefiner.fetch_available_models("http://localhost:11434")
        assert "qwen2.5:7b" in models
        assert "gemma3:4b" in models
