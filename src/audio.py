import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import threading
import queue
import os
import re

from src.config import ConfigManager

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.frames = []
        self.stream = None
        self.volume_callback = None # (volume: float) -> None
        self.max_volume = 0.0 # 録音中の最大音量を追跡

    def start(self, volume_callback=None):
        """録音を開始する"""
        if self.recording:
            return

        device_index = self._resolve_device()

        self.recording = True
        self.frames = []
        self.max_volume = 0.0
        self.volume_callback = volume_callback

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            blocksize=1024,
            device=device_index
        )
        self.stream.start()

    def stop(self) -> str:
        """
        録音を停止し、WAVファイルを保存してパスを返す
        """
        if not self.recording:
            return None
            
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        # 録音データを結合
        if not self.frames:
            return None
            
        recording_data = np.concatenate(self.frames, axis=0)
        
        # 一時ファイルに保存
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        wav.write(temp_file.name, self.sample_rate, recording_data)
        return temp_file.name

    def _audio_callback(self, indata, frames, time, status):
        """ストリームからのコールバック"""
        if status:
            print(status)
        if self.recording:
            self.frames.append(indata.copy())
            
            # 音量計算 (RMS)
            rms = float(np.sqrt(np.mean(indata**2)))
            
            # 最大音量を更新
            if rms > self.max_volume:
                self.max_volume = rms
            
            # 正規化 (適当な係数で0.0-1.0に近づける。入力レベルによるが調整必要)
            # ここではクリッピングも考慮して簡易的に
            volume = rms * 5
            volume = min(1.0, volume)
            
            if self.volume_callback:
                self.volume_callback(volume)

    @staticmethod
    def find_device_index(name: str) -> int | None:
        """デバイス名から WASAPI デバイスのインデックスを優先して解決する。
        WASAPI に見つからない場合は他の API にフォールバックする。
        USB ポート番号の違いは正規化して同一視する。
        """
        all_devices = sd.query_devices()
        wasapi_idx = next(
            (i for i, h in enumerate(sd.query_hostapis()) if 'WASAPI' in h['name']),
            None
        )

        def normalize(s: str) -> str:
            return re.sub(r'\(\d+- ', '(', s).lower()

        name_norm = normalize(name)

        # 1. WASAPI 完全一致
        if wasapi_idx is not None:
            for i, d in enumerate(all_devices):
                if d['max_input_channels'] > 0 and d['hostapi'] == wasapi_idx and d['name'] == name:
                    return i

        # 2. WASAPI 正規化一致
        if wasapi_idx is not None:
            for i, d in enumerate(all_devices):
                if d['max_input_channels'] > 0 and d['hostapi'] == wasapi_idx and normalize(d['name']) == name_norm:
                    return i

        # 3. 任意 API 完全一致（フォールバック）
        for i, d in enumerate(all_devices):
            if d['max_input_channels'] > 0 and d['name'] == name:
                return i

        # 4. 任意 API 正規化一致（フォールバック）
        for i, d in enumerate(all_devices):
            if d['max_input_channels'] > 0 and normalize(d['name']) == name_norm:
                return i

        return None

    def _resolve_device(self) -> int | None:
        """設定からマイクデバイスを解決してインデックスを返す（None = システムデフォルト）"""
        name = ConfigManager.get_mic_device()
        if name is None:
            return None
        idx = AudioRecorder.find_device_index(name)
        if idx is None:
            print(f"[AudioRecorder] mic '{name}' not found, using default")
        return idx
