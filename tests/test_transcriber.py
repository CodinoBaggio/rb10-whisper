import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock
from src.transcriber import Transcriber


@patch('src.transcriber.ConfigManager.get_whisper_url', return_value="http://localhost:8000/v1")
@patch('src.transcriber.OpenAI')
def test_init_uses_local_url(mock_openai, mock_url):
    Transcriber()
    mock_openai.assert_called_once_with(
        api_key="dummy",
        base_url="http://localhost:8000/v1",
        timeout=30.0
    )


@patch('src.transcriber.ConfigManager.get_whisper_url', return_value="http://localhost:8000/v1")
@patch('src.transcriber.OpenAI')
def test_check_connection_returns_true_when_server_is_up(mock_openai, mock_url):
    mock_client = MagicMock()
    mock_client.models.list.return_value = []
    mock_openai.return_value = mock_client

    t = Transcriber()
    assert t.check_connection() is True


@patch('src.transcriber.ConfigManager.get_whisper_url', return_value="http://localhost:8000/v1")
@patch('src.transcriber.OpenAI')
def test_check_connection_returns_false_when_server_is_down(mock_openai, mock_url):
    mock_client = MagicMock()
    mock_client.models.list.side_effect = Exception("Connection refused")
    mock_openai.return_value = mock_client

    t = Transcriber()
    assert t.check_connection() is False
