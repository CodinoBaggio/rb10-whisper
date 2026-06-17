# マイク選択機能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Settings ウィンドウにマイク選択 UI を追加し、OS のデフォルト設定を変えずに rb10-whisper 単体で録音デバイスを切り替えられるようにする。

**Architecture:** `ConfigManager` に `mic_device` (str | None) を追加。`AudioRecorder` に `find_device_index(name)` static メソッドを追加し、完全一致 → regex 正規化フォールバック（USB ポート番号除去）の 2 段解決を実装。`start()` が毎回 `_resolve_device()` を呼んでインデックスを解決し `sd.InputStream(device=)` に渡す。`main.py` の起動チェック・Settings UI の両方で `find_device_index` を再利用する。

**Tech Stack:** Python 3.11, sounddevice, tkinter/ttk, pytest, re (標準ライブラリ)

---

### Task 1: config.py に mic_device サポートを追加

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: test_config.py にテストを追記する**

`tests/test_config.py` の末尾に以下を追記する（既存の import はそのまま流用）:

```python
def test_get_mic_device_returns_none_by_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        device = ConfigManager.get_mic_device()
    assert device is None


def test_get_mic_device_returns_saved_name():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={"mic_device": "Microphone (Blue Yeti)"}):
        device = ConfigManager.get_mic_device()
    assert device == "Microphone (Blue Yeti)"


def test_set_mic_device_saves_name(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_mic_device("Microphone (Blue Yeti)")
    ConfigManager._config_cache = None
    assert ConfigManager.get_mic_device() == "Microphone (Blue Yeti)"


def test_set_mic_device_saves_none(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_mic_device(None)
    ConfigManager._config_cache = None
    assert ConfigManager.get_mic_device() is None
```

- [ ] **Step 2: テストが失敗することを確認する**

```
cd "C:\Users\kensho\Documents\My Projects\rb10-whisper"
pytest tests/test_config.py -v -k "mic_device"
```

Expected: 4 FAILED (get_mic_device not defined)

- [ ] **Step 3: config.py を実装する**

`src/config.py` の `load_config()` 内 `defaults` を以下に変更する:

```python
defaults = {
    "hotkey": "shift",
    "whisper_url": "http://localhost:8000/v1",
    "whisper_model": "Systran/faster-whisper-large-v3",
    "mic_device": None
}
```

ファイル末尾（`get_whisper_model` の後）に以下を追加する:

```python
    @classmethod
    def get_mic_device(cls) -> str | None:
        """録音に使用するマイクのデバイス名を取得（None = システムデフォルト）"""
        config = cls.load_config()
        return config.get("mic_device", None)

    @classmethod
    def set_mic_device(cls, name: str | None) -> None:
        """マイクのデバイス名を設定に保存（None = システムデフォルト）"""
        config = cls.load_config()
        config["mic_device"] = name
        cls.save_config(config)
```

- [ ] **Step 4: テストが通ることを確認する**

```
pytest tests/test_config.py -v -k "mic_device"
```

Expected: 4 PASSED

- [ ] **Step 5: コミット**

```
git add src/config.py tests/test_config.py
git commit -m "feat: add mic_device support to ConfigManager"
```

---

### Task 2: audio.py に find_device_index() と _resolve_device() を追加

**Files:**
- Modify: `src/audio.py`
- Create: `tests/test_audio.py`

- [ ] **Step 1: tests/test_audio.py を新規作成する**

```python
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


# --- find_device_index のテスト ---

def test_find_device_index_exact_match():
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = AudioRecorder.find_device_index('Microphone (Blue Yeti)')
    assert result == 1


def test_find_device_index_normalized_match_on_port_change():
    # USBドックのポート変更で "(Blue Yeti)" が "(2- Blue Yeti)" になるケース
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES_PORT_CHANGED):
        result = AudioRecorder.find_device_index('Microphone (Blue Yeti)')
    assert result == 1  # MOCK_DEVICES_PORT_CHANGED[1]


def test_find_device_index_not_found_returns_none():
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = AudioRecorder.find_device_index('Nonexistent Mic')
    assert result is None


def test_find_device_index_skips_output_only_devices():
    with patch('sounddevice.query_devices', return_value=MOCK_DEVICES):
        result = AudioRecorder.find_device_index('Speakers (Realtek)')
    assert result is None


# --- _resolve_device のテスト ---

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
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_audio.py -v
```

Expected: 8 FAILED (find_device_index not defined)

- [ ] **Step 3: audio.py を実装する**

`src/audio.py` の先頭 import に `import re` を追加する:

```python
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import threading
import queue
import os
import re
```

`AudioRecorder` クラスの `__init__` の直前に `from src.config import ConfigManager` の import を追加する（クラス定義の上）:

```python
from src.config import ConfigManager
```

`start()` メソッドを以下に変更する（`device_index = self._resolve_device()` を追加し `sd.InputStream` に渡す）:

```python
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
```

`_audio_callback` の後（クラス末尾）に以下 2 つのメソッドを追加する:

```python
    @staticmethod
    def find_device_index(name: str) -> int | None:
        """デバイス名からインデックスを解決する。
        完全一致優先。見つからない場合は USB ポート番号を正規化して再比較する。
        例: "(Blue Yeti)" と "(2- Blue Yeti)" は同一デバイスと判定する。
        入力チャンネルなし（出力専用）デバイスは除外する。
        """
        all_devices = sd.query_devices()

        for i, d in enumerate(all_devices):
            if d['max_input_channels'] > 0 and d['name'] == name:
                return i

        def normalize(s: str) -> str:
            return re.sub(r'\(\d+- ', '(', s).lower()

        name_norm = normalize(name)
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
```

- [ ] **Step 4: テストが通ることを確認する**

```
pytest tests/test_audio.py -v
```

Expected: 8 PASSED

- [ ] **Step 5: 全テストが通ることを確認する**

```
pytest tests/ -v
```

Expected: 全テスト PASSED

- [ ] **Step 6: コミット**

```
git add src/audio.py tests/test_audio.py
git commit -m "feat: add mic device resolution to AudioRecorder"
```

---

### Task 3: main.py に起動時マイクチェックを追加

**Files:**
- Modify: `src/main.py`

UI ダイアログを含む起動フローは統合テストの領域のため unit test は不要。

- [ ] **Step 1: `_check_mic_on_startup()` を追加する**

`src/main.py` の `_check_connection_on_startup()` メソッド（現 276 行）の直後に以下を追加する:

```python
    def _check_mic_on_startup(self):
        """起動時に設定されたマイクが存在するか確認"""
        name = ConfigManager.get_mic_device()
        if name is None:
            return
        if self.recorder.find_device_index(name) is None:
            import tkinter.messagebox
            tkinter.messagebox.showwarning(
                "マイクが見つかりません",
                f"設定されたマイク「{name}」が見つかりません。\n"
                "システムデフォルトを使用します。"
            )
```

- [ ] **Step 2: `__init__` から呼び出す**

`src/main.py` の `self._check_connection_on_startup()` の行（現 155 行）の直後に以下を追加する:

```python
        self._check_mic_on_startup()
```

- [ ] **Step 3: コミット**

```
git add src/main.py
git commit -m "feat: add mic availability check on startup"
```

---

### Task 4: ui.py に Microphone セクションを追加

**Files:**
- Modify: `src/ui.py`

Tkinter UI は手動確認で検証する。

- [ ] **Step 1: `src/ui.py` の先頭 import に sounddevice を追加する**

```python
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser
import sounddevice as sd
from src.config import ConfigManager
import math
import keyboard
import threading
```

- [ ] **Step 2: `_setup_ui()` に Microphone セクションを追加する**

`_setup_ui()` 内の `# 下部の閉じるボタンエリア` コメントの直前（現 119 行付近）に以下を挿入する:

```python
        # マイク選択コンテナ
        mic_container = tk.Frame(self.window, padx=20, pady=10, bg=bg_color)
        mic_container.pack(fill='x')

        tk.Label(mic_container, text="Microphone:", bg=bg_color, fg=fg_color).pack(anchor='w')

        mic_row = tk.Frame(mic_container, bg=bg_color)
        mic_row.pack(fill='x', pady=5)

        system_default = "System Default"
        try:
            all_devices = sd.query_devices()
            input_device_names = [
                d['name'] for d in all_devices if d['max_input_channels'] > 0
            ]
        except Exception:
            input_device_names = []
        mic_options = [system_default] + input_device_names

        current_mic = ConfigManager.get_mic_device()
        initial_mic = current_mic if current_mic in input_device_names else system_default
        self.mic_var = tk.StringVar(value=initial_mic)

        self.mic_combo = ttk.Combobox(mic_row, textvariable=self.mic_var,
                                      values=mic_options, state="readonly")
        self.mic_combo.pack(side=tk.LEFT, fill='x', expand=True, ipady=3)

        self.btn_apply_mic = tk.Button(mic_row, text="Apply Mic", command=self._apply_mic,
                                       bg=btn_bg, fg="white", activebackground=btn_active,
                                       relief=tk.FLAT, width=12,
                                       font=("Helvetica", 10, "bold"), cursor="hand2")
        self.btn_apply_mic.pack(side=tk.LEFT, padx=(10, 0))

        lbl_mic_desc = tk.Label(mic_container,
                                text="設定を変更したら「Apply Mic」を押してください",
                                bg=bg_color, fg="#aaaaaa", font=("Helvetica", 9),
                                justify=tk.LEFT)
        lbl_mic_desc.pack(anchor='w')
```

- [ ] **Step 3: `_apply_mic()` メソッドを追加する**

`_apply_hotkey()` メソッドの直後に以下を追加する:

```python
    def _apply_mic(self):
        """マイク設定を適用"""
        selected = self.mic_var.get().strip()
        if not selected:
            return

        self._set_cursor("watch")

        def task():
            try:
                name_to_save = None if selected == "System Default" else selected
                ConfigManager.set_mic_device(name_to_save)
                label = "System Default" if name_to_save is None else selected
                self.window.after(0, lambda: self._on_save_completed(f"Mic [{label}] applied!"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", f"Failed to apply mic: {e}"))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))

        threading.Thread(target=task, daemon=True).start()
```

- [ ] **Step 4: アプリを起動して手動確認する**

`launcher.py` を起動 → システムトレイ右クリック → Settings を開く。

確認項目:
- [ ] Microphone セクションが hotkey セクションの下に表示される
- [ ] コンボボックスに "System Default" と接続中のマイクが列挙される
- [ ] 現在の設定値が初期選択されている
- [ ] "Apply Mic" を押すと成功ダイアログが出てウィンドウが閉じる
- [ ] `%APPDATA%\rb10-whisper\settings.json` を確認して `mic_device` が保存されている
- [ ] アプリを再起動してホットキーで録音 → 選択したマイクで録音されているか確認

- [ ] **Step 5: コミット**

```
git add src/ui.py
git commit -m "feat: add microphone selection to Settings UI"
```

---

### Task 5: 統合確認・チケット更新

**Files:**
- Create: `G:\マイドライブ\ワークスペース\プロジェクトルーム\東商会エンジニアリング\音声入力ツール\tickets\completed\2026-06-11_mic-selection.md`
- Modify: `G:\マイドライブ\ワークスペース\プロジェクトルーム\東商会エンジニアリング\音声入力ツール\status.md`

- [ ] **Step 1: 全テストを実行する**

```
cd "C:\Users\kensho\Documents\My Projects\rb10-whisper"
pytest tests/ -v
```

Expected: 全テスト PASSED（test_config: 6, test_transcriber: 3, test_audio: 8 = 計 17）

- [ ] **Step 2: プロジェクトチケットを作成する**

`G:\マイドライブ\ワークスペース\プロジェクトルーム\東商会エンジニアリング\音声入力ツール\tickets\completed\2026-06-11_mic-selection.md` を作成し以下を記録する:

```markdown
# マイク選択機能

- ID: 2026-06-11_mic-selection
- 優先度: 中
- ステータス: completed
- 担当者: 東（Claude 実装）
- 作成日: 2026-06-11
- 完了日: 2026-06-11

## 概要

Settings ウィンドウにマイク選択 UI を追加し、OS のデフォルト設定を変えずに
rb10-whisper 単体で録音デバイスを切り替えられるようにする。

## 実施内容

| ファイル | 変更内容 |
|---|---|
| src/config.py | mic_device 追加、get_mic_device() / set_mic_device() 追加 |
| src/audio.py | find_device_index() static メソッド追加、_resolve_device() 追加、start() 更新 |
| src/main.py | _check_mic_on_startup() 追加 |
| src/ui.py | Microphone セクション追加、_apply_mic() 追加 |

## 再利用可能な学び

[INSIGHT] USB ドック経由のデバイスはポート変更で名前が変わる（"(Blue Yeti)" → "(2- Blue Yeti)"）。
re.sub(r'\(\d+- ', '(', name) で正規化すると同一デバイスとして判定できる。
[INSIGHT] sounddevice.query_devices() は入力・出力混在リストを返す。
max_input_channels > 0 でフィルタしないと出力専用デバイスが混入する。
```

- [ ] **Step 3: status.md を更新する**

`G:\マイドライブ\ワークスペース\プロジェクトルーム\東商会エンジニアリング\音声入力ツール\status.md` の `next_action` を以下に更新する:

```
next_action: feature/local-speaches-backend を main にマージする
related_ticket: tickets/completed/2026-06-11_mic-selection.md
```
