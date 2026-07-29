import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.transcriber import Transcriber


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


@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_passes_no_selection_to_llm_refiner(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url
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


@patch("src.transcriber.ConfigManager.get_whisper_url", return_value="http://localhost:8000/v1")
@patch("src.transcriber.OpenAI")
@patch("src.transcriber.LLMRefiner")
@patch("builtins.open", new_callable=MagicMock)
def test_transcribe_passes_selected_text_to_llm_refiner(
    mock_open, mock_llm_refiner_cls, mock_openai, mock_url
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
