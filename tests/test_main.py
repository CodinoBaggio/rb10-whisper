import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import AudioInputApp


@patch("src.main.ConfigManager.get_ai_mode", return_value="edit")
@patch("src.main.time.sleep")
@patch("src.main.time.time_ns", return_value=123)
@patch("src.main.pyautogui.hotkey")
@patch("src.main.pyperclip.copy")
@patch("src.main.pyperclip.paste", side_effect=["previous clipboard", "selected text"])
def test_capture_ai_edit_selection_returns_selection_and_restores_clipboard(
    mock_paste, mock_copy, mock_hotkey, mock_time_ns, mock_sleep, mock_mode
):
    app = AudioInputApp.__new__(AudioInputApp)

    selected = app._capture_ai_edit_selection()

    assert selected == "selected text"
    mock_hotkey.assert_called_once_with("ctrl", "c")
    assert mock_copy.call_count == 2
    assert mock_copy.call_args_list[-1].args == ("previous clipboard",)
    assert mock_sleep.called


@patch("src.main.ConfigManager.get_ai_mode", return_value="edit")
@patch("src.main.time.sleep")
@patch("src.main.time.time_ns", return_value=123)
@patch("src.main.pyautogui.hotkey")
@patch("src.main.pyperclip.copy")
@patch("src.main.pyperclip.paste")
def test_capture_ai_edit_selection_returns_none_when_copy_did_not_change_clipboard(
    mock_paste, mock_copy, mock_hotkey, mock_time_ns, mock_sleep, mock_mode
):
    clipboard = {"value": "previous clipboard"}

    def copy(value):
        clipboard["value"] = value

    mock_copy.side_effect = copy
    mock_paste.side_effect = lambda: clipboard["value"]
    app = AudioInputApp.__new__(AudioInputApp)

    selected = app._capture_ai_edit_selection()

    assert selected is None
    assert clipboard["value"] == "previous clipboard"