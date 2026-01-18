import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import threading
import queue
import os

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.frames = []
        self.stream = None
        self.volume_callback = None # (volume: float) -> None

    def start(self, volume_callback=None):
        """録音を開始する"""
        if self.recording:
            return
        
        self.recording = True
        self.frames = []
        self.volume_callback = volume_callback
        
        # ストリームの開始
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            blocksize=1024
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
            rms = np.sqrt(np.mean(indata**2))
            
            # 正規化 (適当な係数で0.0-1.0に近づける。入力レベルによるが調整必要)
            # ここではクリッピングも考慮して簡易的に
            volume = float(rms) * 10
            volume = min(1.0, volume)
            
            if self.volume_callback:
                self.volume_callback(volume)
