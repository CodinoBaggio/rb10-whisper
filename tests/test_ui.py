import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui import SettingsWindow


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
