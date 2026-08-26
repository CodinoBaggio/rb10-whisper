import os
import sys
import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.ui as ui
from src.ui import OverlayWindow, SettingsWindow


class _Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Widget:
    def __init__(self):
        self.config_calls = []

    def destroy(self):
        pass

    def pack(self, **kwargs):
        pass

    def config(self, **kwargs):
        self.config_calls.append(kwargs)


class _Combobox(_Widget):
    def __init__(self, *args, **kwargs):
        super().__init__()


class _Window:
    def winfo_exists(self):
        return True


class _CallbackWindow(_Window):
    def __init__(self):
        self.callbacks = []

    def after(self, delay, callback):
        self.callbacks.append(callback)


class _Thread:
    scheduled = []

    def __init__(self, target, args, daemon):
        self.target = target
        self.args = args

    def start(self):
        self.scheduled.append((self.target, self.args))


def _settings_window(current_model, prefetched_model):
    window = SettingsWindow.__new__(SettingsWindow)
    window.window = _Window()
    window.model_var = _Value(current_model)
    window._prefetch_model_value = prefetched_model
    window.model_widget = _Widget()
    window.model_row = object()
    window.backend_var = _Value("local")
    window._prevent_combobox_wheel_scroll = lambda widget: None
    return window


def _models_response(models):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = (
        ('{"data": ' + str([{"id": model} for model in models]).replace("'", '"') + '}').encode()
    )
    return response


def _user32_mock(mock_windll):
    user32 = mock_windll.user32
    user32.GetCursorPos.return_value = 1
    user32.MonitorFromPoint.return_value = 1
    user32.GetMonitorInfoW.return_value = 1
    return user32


@patch("src.ui.ctypes.windll")
def test_get_cursor_monitor_rect_returns_rc_monitor_and_uses_nearest_flag(mock_windll):
    user32 = _user32_mock(mock_windll)

    def fill_monitor_info(monitor, monitor_info_ptr):
        monitor_info = monitor_info_ptr._obj
        monitor_info.rcMonitor.left = -2560
        monitor_info.rcMonitor.top = 0
        monitor_info.rcMonitor.right = 0
        monitor_info.rcMonitor.bottom = 1440
        monitor_info.rcWork.left = -2500
        monitor_info.rcWork.top = 10
        monitor_info.rcWork.right = -10
        monitor_info.rcWork.bottom = 1392
        return 1

    user32.GetMonitorInfoW.side_effect = fill_monitor_info

    monitor_rect = ui.get_cursor_monitor_rect()

    assert monitor_rect == (-2560, 0, 0, 1440)
    assert user32.MonitorFromPoint.call_args.args[1] == 2


@patch("src.ui.ctypes.windll")
def test_get_cursor_monitor_rect_raises_when_get_cursor_pos_returns_zero(mock_windll):
    user32 = _user32_mock(mock_windll)
    user32.GetCursorPos.return_value = 0

    with pytest.raises(OSError, match="GetCursorPos failed"):
        ui.get_cursor_monitor_rect()


@patch("src.ui.ctypes.windll")
def test_get_cursor_monitor_rect_raises_when_monitor_from_point_returns_zero(mock_windll):
    user32 = _user32_mock(mock_windll)
    user32.MonitorFromPoint.return_value = 0

    with pytest.raises(OSError, match="MonitorFromPoint failed"):
        ui.get_cursor_monitor_rect()


@patch("src.ui.ctypes.windll")
def test_get_cursor_monitor_rect_raises_when_get_monitor_info_returns_zero(mock_windll):
    user32 = _user32_mock(mock_windll)
    user32.GetMonitorInfoW.return_value = 0

    with pytest.raises(OSError, match="GetMonitorInfoW failed"):
        ui.get_cursor_monitor_rect()


def test_calc_overlay_position_keeps_primary_monitor_position():
    position = ui.calc_overlay_position((0, 0, 2560, 1440), 320, 80, 120)

    assert position == (1120, 1240)


def test_calc_overlay_position_handles_negative_coordinate_monitor():
    position = ui.calc_overlay_position((-2560, 0, 0, 1440), 320, 80, 120)

    assert position == (-1440, 1240)


def test_calc_overlay_position_centers_and_keeps_bottom_offset_on_different_resolution():
    position = ui.calc_overlay_position((2560, 200, 4480, 1280), 320, 80, 120)

    assert position == (3360, 1080)


@patch("src.ui.get_cursor_monitor_rect", return_value=(-2560, 0, 0, 1440))
def test_reposition_for_cursor_uses_cursor_monitor_rect(mock_monitor_rect):
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay.window = MagicMock()

    overlay._reposition_for_cursor()

    overlay.window.geometry.assert_called_once_with("320x80+-1440+1240")


@patch("src.ui.get_cursor_monitor_rect", side_effect=OSError("Win32 failed"))
def test_reposition_for_cursor_falls_back_to_primary_screen(mock_monitor_rect):
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay.window = MagicMock()
    overlay.window.winfo_screenwidth.return_value = 2560
    overlay.window.winfo_screenheight.return_value = 1440

    overlay._reposition_for_cursor()

    overlay.window.geometry.assert_called_once_with("320x80+1120+1240")


def test_show_repositions_overlay_before_deiconify():
    overlay = OverlayWindow.__new__(OverlayWindow)
    call_order = []
    overlay.window = MagicMock()
    overlay.window.deiconify.side_effect = lambda: call_order.append("deiconify")
    overlay.canvas = MagicMock()
    overlay.bars = []
    overlay.rec_colors = []
    overlay._reposition_for_cursor = lambda: call_order.append("reposition")
    overlay._draw_frame = MagicMock()

    overlay.show()

    assert call_order == ["reposition", "deiconify"]


@patch("src.ui.ttk.Combobox", return_value=_Widget())
def test_switch_to_model_combo_keeps_prefetched_saved_model_when_available(mock_combo):
    window = _settings_window("Fetching...", "Systran/faster-whisper-large-v3")

    window._switch_to_model_combo([
        "deepdml/faster-whisper-large-v3-turbo-ct2",
        "Systran/faster-whisper-large-v3",
    ])

    assert window.model_var.get() == "Systran/faster-whisper-large-v3"


@patch("src.ui.ttk.Combobox", return_value=_Widget())
def test_switch_to_model_combo_falls_back_to_first_model_when_saved_model_is_missing(mock_combo):
    window = _settings_window("Fetching...", "missing-model")

    window._switch_to_model_combo([
        "deepdml/faster-whisper-large-v3-turbo-ct2",
        "Systran/faster-whisper-large-v3",
    ])

    assert window.model_var.get() == "deepdml/faster-whisper-large-v3-turbo-ct2"


@patch("src.ui.ttk.Combobox", return_value=_Widget())
def test_switch_to_model_combo_keeps_current_model_over_prefetched_model(mock_combo):
    window = _settings_window(
        "Systran/faster-whisper-large-v3",
        "deepdml/faster-whisper-large-v3-turbo-ct2",
    )

    window._switch_to_model_combo([
        "deepdml/faster-whisper-large-v3-turbo-ct2",
        "Systran/faster-whisper-large-v3",
    ])

    assert window.model_var.get() == "Systran/faster-whisper-large-v3"


@patch("src.ui.threading.Thread", _Thread)
@patch("src.ui.ttk.Combobox", return_value=_Widget())
@patch("urllib.request.urlopen")
def test_latest_fetch_keeps_original_saved_model_after_consecutive_fetches(
    mock_urlopen, mock_combo
):
    _Thread.scheduled = []
    window = _settings_window("Systran/faster-whisper-large-v3", None)
    window.window = _CallbackWindow()
    mock_urlopen.return_value = _models_response([
        "deepdml/faster-whisper-large-v3-turbo-ct2",
        "Systran/faster-whisper-large-v3",
    ])

    window._start_model_fetch("http://localhost:8001/v1")
    window._start_model_fetch("http://localhost:8001/v1")
    target, args = _Thread.scheduled[-1]
    target(*args)
    window.window.callbacks.pop()()

    assert window.model_var.get() == "Systran/faster-whisper-large-v3"


@patch("src.ui.threading.Thread", _Thread)
@patch("src.ui.ttk.Combobox", return_value=_Widget())
@patch("urllib.request.urlopen")
def test_stale_fetch_callback_does_not_update_model_after_new_fetch_starts(
    mock_urlopen, mock_combo
):
    _Thread.scheduled = []
    window = _settings_window("Systran/faster-whisper-large-v3", None)
    window.window = _CallbackWindow()
    mock_urlopen.return_value = _models_response([
        "deepdml/faster-whisper-large-v3-turbo-ct2",
        "Systran/faster-whisper-large-v3",
    ])

    window._start_model_fetch("http://localhost:8001/v1")
    old_target, old_args = _Thread.scheduled[-1]
    old_target(*old_args)
    window._start_model_fetch("http://localhost:8001/v1")
    window.window.callbacks.pop()()

    assert window.model_var.get() == "Fetching..."


@patch("src.ui.threading.Thread", _Thread)
@patch("urllib.request.urlopen", side_effect=OSError("connection failed"))
def test_stale_failed_fetch_callback_does_not_reenable_model_after_new_fetch_starts(
    mock_urlopen
):
    _Thread.scheduled = []
    window = _settings_window("Systran/faster-whisper-large-v3", None)
    window.window = _CallbackWindow()
    model_widget = window.model_widget

    window._start_model_fetch("http://localhost:8001/v1")
    old_target, old_args = _Thread.scheduled[-1]
    old_target(*old_args)
    window._start_model_fetch("http://localhost:8001/v1")
    window.window.callbacks.pop()()

    assert model_widget.config_calls == [{"state": "disabled"}, {"state": "disabled"}]


@patch("src.ui.threading.Thread", _Thread)
@patch("src.ui.ttk.Combobox", _Combobox)
@patch("urllib.request.urlopen")
@patch("src.ui.ConfigManager.get_whisper_model", return_value="manual-entry-model")
def test_nonlocal_url_blur_invalidates_queued_fetch_callback(
    mock_saved_model, mock_urlopen
):
    _Thread.scheduled = []
    window = _settings_window("Systran/faster-whisper-large-v3", None)
    window.window = _CallbackWindow()
    window.local_url_var = _Value("https://api.example.com/v1")
    mock_urlopen.return_value = _models_response(["old-local-model"])

    window._start_model_fetch("http://localhost:8001/v1")
    fetch_target, fetch_args = _Thread.scheduled[-1]
    fetch_target(*fetch_args)
    window._on_url_blur(None)
    window.window.callbacks.pop()()

    assert window.model_var.get() == "manual-entry-model"


@patch.object(SettingsWindow, "_on_backend_change")
@patch.object(SettingsWindow, "_load_dictionary_rows")
@patch("src.ui.ConfigManager")
@patch("src.ui.sd.query_devices", return_value=[])
@patch("src.ui.ttk.Combobox")
@patch("src.ui.ttk.Scrollbar")
@patch("src.ui.ttk.Style")
@patch("src.ui.tk.StringVar")
@patch("src.ui.tk.Radiobutton")
@patch("src.ui.tk.Entry")
@patch("src.ui.tk.Canvas")
@patch("src.ui.tk.Button")
@patch("src.ui.tk.Label")
@patch("src.ui.tk.Frame")
def test_setup_ui_shows_version_from_definition_in_fixed_bottom_area(
    mock_frame,
    mock_label,
    mock_button,
    mock_canvas,
    mock_entry,
    mock_radiobutton,
    mock_string_var,
    mock_style,
    mock_scrollbar,
    mock_combobox,
    mock_query_devices,
    mock_config_manager,
    mock_load_dictionary_rows,
    mock_on_backend_change,
):
    """Version must be in the fixed footer and use the imported definition."""
    window = SettingsWindow.__new__(SettingsWindow)
    window.window = MagicMock()
    labels_by_text = {}
    buttons_by_text = {}
    frames = []
    mock_config_manager.get_backend_type.return_value = "openai"
    mock_config_manager.get_openai_url.return_value = "https://api.example.com/v1"
    mock_config_manager.load_api_key.return_value = "test-key"
    mock_config_manager.get_whisper_url.return_value = "http://localhost:8001/v1"
    mock_config_manager.get_whisper_model.return_value = "test-model"
    mock_config_manager.get_docker_container.return_value = ""
    mock_config_manager.get_hotkey.return_value = "alt+x"
    mock_config_manager.get_hotkey_toggle.return_value = "alt+z"
    mock_config_manager.parse_hotkey.return_value = ("alt", "x")
    mock_config_manager.get_mic_device.return_value = ""
    mock_config_manager.get_ai_mode.return_value = "off"
    mock_config_manager.get_ollama_model.return_value = ""
    mock_config_manager.get_ollama_url.return_value = ""

    def create_frame(*args, **kwargs):
        frame = MagicMock()
        frames.append((args, frame))
        return frame

    def create_label(*args, **kwargs):
        label = MagicMock()
        labels_by_text[kwargs.get("text")] = (args, label)
        return label

    def create_button(*args, **kwargs):
        button = MagicMock()
        buttons_by_text[kwargs.get("text")] = (args, kwargs, button)
        return button

    mock_frame.side_effect = create_frame
    mock_label.side_effect = create_label
    mock_button.side_effect = create_button

    with patch("src.ui.APP_VERSION", "9.9.9"):
        window._setup_ui()

    footer_args, footer = frames[0]
    assert footer_args == (window.window,)
    footer.pack.assert_called_once_with(side=tk.BOTTOM, fill="x")

    version_label_args, version_label = labels_by_text["Version 9.9.9"]
    assert version_label_args == (footer,)
    version_label.pack.assert_called_once_with(side=tk.LEFT)

    close_button_args, close_button_kwargs, close_button = buttons_by_text["Close Settings"]
    assert close_button_args == (footer,)
    assert close_button_kwargs["command"].__self__ is window
    assert close_button_kwargs["command"].__func__ is SettingsWindow._on_close_clicked
    close_button.pack.assert_called_once_with(side=tk.RIGHT)
