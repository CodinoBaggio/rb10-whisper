import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.transcriber import Transcriber
from src.dictionary import Dictionary


@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
def test_init_uses_local_url(mock_openai, mock_url):
    transcriber = Transcriber()
    transcriber._make_client()
    mock_openai.assert_called_once_with(
        api_key="dummy",
        base_url="http://localhost:8000/v1",
        timeout=30.0,
    )


@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
def test_check_connection_returns_true_when_server_is_up(mock_openai, mock_url):
    mock_client = MagicMock()
    mock_client.models.list.return_value = []
    mock_openai.return_value = mock_client

    assert Transcriber().check_connection() is True


@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
def test_check_connection_returns_false_when_server_is_down(mock_openai, mock_url):
    mock_client = MagicMock()
    mock_client.models.list.side_effect = Exception("Connection refused")
    mock_openai.return_value = mock_client

    assert Transcriber().check_connection() is False


@patch("src.transcriber.ConfigManager.get_dictionary", return_value=[])
@patch("src.transcriber.ConfigManager.get_whisper_model", return_value="Systran/faster-whisper-large-v3")
@patch("src.transcriber.ConfigManager.get_backend_type", return_value="local")
@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_passes_configured_model_to_api(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url, mock_backend,
    mock_model, mock_dict
):
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value.text = "テストです"
    mock_openai.return_value = mock_client
    mock_llm_refiner_cls.return_value.refine.return_value = "テストです。"

    Transcriber().transcribe("dummy_file.wav")

    assert mock_client.audio.transcriptions.create.call_args.kwargs["model"] == (
        "Systran/faster-whisper-large-v3"
    )


@patch("src.transcriber.ConfigManager.get_dictionary", return_value=[])
@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_passes_no_selection_to_llm_refiner(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url, mock_dict
):
    mock_client = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.text = "こんにちは えーテストです"
    mock_client.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_client
    mock_refiner_inst = MagicMock()
    mock_refiner_inst.refine.return_value = "こんにちはテストです。"
    mock_llm_refiner_cls.return_value = mock_refiner_inst

    result = Transcriber().transcribe("dummy_file.wav")

    assert result == "こんにちはテストです。"
    mock_refiner_inst.refine.assert_called_once_with("こんにちは テストです", None)


@patch("src.transcriber.ConfigManager.get_dictionary", return_value=[])
@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_passes_selected_text_to_llm_refiner(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url, mock_dict
):
    mock_client = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.text = "丁寧にして"
    mock_client.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_client
    mock_refiner_inst = MagicMock()
    mock_refiner_inst.refine.return_value = "選択した文を丁寧にした結果"
    mock_llm_refiner_cls.return_value = mock_refiner_inst

    result = Transcriber().transcribe("dummy_file.wav", selected_text="これは選択中の文です")

    assert result == "選択した文を丁寧にした結果"
    mock_refiner_inst.refine.assert_called_once_with("丁寧にして", "これは選択中の文です")


@patch("src.transcriber.ConfigManager.get_dictionary", return_value=[
    {"term": "Anthropic", "wrong": "あんそろぴっく"},
    {"term": "東商会", "wrong": ""},
])
@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_injects_dictionary_terms_into_prompt(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url, mock_dict
):
    mock_client = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.text = "テストです"
    mock_client.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_client
    mock_llm_refiner_cls.return_value.refine.return_value = "テストです。"

    Transcriber().transcribe("dummy_file.wav")

    prompt = mock_client.audio.transcriptions.create.call_args.kwargs["prompt"]
    assert "Anthropic" in prompt
    assert "東商会" in prompt
    assert prompt.startswith("こんにちは。")


@patch("src.transcriber.ConfigManager.get_dictionary", return_value=[])
@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_prompt_unchanged_when_dictionary_is_empty(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url, mock_dict
):
    mock_client = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.text = "テストです"
    mock_client.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_client
    mock_llm_refiner_cls.return_value.refine.return_value = "テストです。"

    Transcriber().transcribe("dummy_file.wav")

    prompt = mock_client.audio.transcriptions.create.call_args.kwargs["prompt"]
    assert prompt == "こんにちは。"


@patch("src.transcriber.ConfigManager.get_dictionary", return_value=[
    {"term": "Anthropic", "wrong": "あんそろぴっく"},
])
@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_passes_replaced_text_to_llm_refiner(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url, mock_dict
):
    mock_client = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.text = "あんそろぴっくのAPIを使う"
    mock_client.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_client
    mock_refiner_inst = MagicMock()
    mock_refiner_inst.refine.return_value = "AnthropicのAPIを使う。"
    mock_llm_refiner_cls.return_value = mock_refiner_inst

    result = Transcriber().transcribe("dummy_file.wav")

    assert result == "AnthropicのAPIを使う。"
    mock_refiner_inst.refine.assert_called_once_with("AnthropicのAPIを使う", None)


@patch("src.transcriber.ConfigManager.get_dictionary", return_value=[
    {"term": "Anthropic", "wrong": "アントロピック"},
])
@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_applies_dictionary_after_filler_removal(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url, mock_dict
):
    # フィラー除去後にはじめて "アントロピック" が成立する文字列。
    # 置換がフィラー除去より前だと一致せず "アントロピック" のまま残る。
    mock_client = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.text = "アンえートロピックの話"
    mock_client.audio.transcriptions.create.return_value = mock_transcript
    mock_openai.return_value = mock_client
    mock_refiner_inst = MagicMock()
    mock_refiner_inst.refine.return_value = "Anthropicの話。"
    mock_llm_refiner_cls.return_value = mock_refiner_inst

    Transcriber().transcribe("dummy_file.wav")

    mock_refiner_inst.refine.assert_called_once_with("Anthropicの話", None)


# --- J: _post_process が Dictionary.FILLER_PATTERNS を参照している ---

@patch("src.transcriber.Dictionary.FILLER_PATTERNS", ["カスタムフィラー"])
def test_post_process_uses_dictionary_filler_patterns():
    """Dictionary.FILLER_PATTERNS を書き換えると _post_process の挙動が追従すること。"""
    result = Transcriber()._post_process("これはカスタムフィラーですテスト")
    assert "カスタムフィラー" not in result
    # 差し替え後は元の "えー" 等はもうフィラー扱いされない
    result2 = Transcriber()._post_process("これはえーですテスト")
    assert "えー" in result2
