import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from src.audio import AudioRecorder

MOCK_DEVICES = [
    {'name': 'Microsoft Sound Mapper - Input', 'max_input_channels': 1, 'max_output_channels': 0},
    {'name': 'Microphone (Blue Yeti)',          'max_input_channels': 2, 'max_output_channels': 0},
    {'name': 'Stereo Mix (Realtek)',             'max_input_channels': 2, 'max_output_channels': 0},
    {'name': 'Speakers (Realtek)',               'max_input_channels': 0, 'max_output_channels': 2},
]

MOCK_DEVICES_PORT_CHANGED = [
    {'name': 'Microsoft Sound Mapper - Input', 'max_input_channels': 1, 'max_output_channels': 0},
    {'name': 'Microphone (2- Blue Yeti)',       'max_input_channels': 2, 'max_output_channels': 0},
    {'name': 'Stereo Mix (Realtek)',             'max_input_channels': 2, 'max_output_channels': 0},
    {'name': 'Speakers (Realtek)',               'max_input_channels': 0, 'max_output_channels': 2},
]


def test_find_device_index_exact_match():
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = AudioRecorder.find_device_index('Microphone (Blue Yeti)')
    assert result == 1


def test_find_device_index_normalized_match_on_port_change():
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES_PORT_CHANGED):
        result = AudioRecorder.find_device_index('Microphone (Blue Yeti)')
    assert result == 1


def test_find_device_index_not_found_returns_none():
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = AudioRecorder.find_device_index('Nonexistent Mic')
    assert result is None


def test_find_device_index_skips_output_only_devices():
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = AudioRecorder.find_device_index('Speakers (Realtek)')
    assert result is None


def test_resolve_device_returns_none_when_mic_device_not_set():
    recorder = AudioRecorder()
    with patch('src.audio.ConfigManager.get_mic_device', return_value=None):
        result = recorder._resolve_device()
    assert result is None


def test_resolve_device_returns_index_when_device_found():
    recorder = AudioRecorder()
    with patch('src.audio.ConfigManager.get_mic_device', return_value='Microphone (Blue Yeti)'), \
         patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = recorder._resolve_device()
    assert result == 1


def test_resolve_device_returns_none_when_device_not_found():
    recorder = AudioRecorder()
    with patch('src.audio.ConfigManager.get_mic_device', return_value='Nonexistent Mic'), \
         patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = recorder._resolve_device()
    assert result is None
