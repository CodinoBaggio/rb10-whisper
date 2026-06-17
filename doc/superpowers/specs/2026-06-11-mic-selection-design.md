# マイク選択機能 設計書

- 作成日: 2026-06-11
- ブランチ: feature/local-speaches-backend（現在作業中ブランチに追加）

## 概要

Settings ウィンドウにマイク選択 UI を追加し、OS の規定デバイスに依存せず録音デバイスを rb10-whisper 単体で切り替えられるようにする。

## 背景・動機

現状、`AudioRecorder` は `sounddevice.InputStream(device=None)` で常に OS の「規定の録音デバイス」を使用する。Bluetooth ヘッドセット・USB マイク・内蔵マイクを用途によって切り替えたい場合、OS のサウンド設定を変更しなければならない。本機能でアプリ内完結の切り替えを実現する。

## アーキテクチャ

アプローチ A を採用: `AudioRecorder.start()` が `ConfigManager.get_mic_device()` を直接読んでデバイスを解決する。`transcriber.py` が `get_whisper_model()` を内部で呼ぶパターンと一致し、`main.py` への変更を最小化する。

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `src/config.py` | `mic_device` をデフォルト設定に追加、`get_mic_device()` / `set_mic_device()` 追加 |
| `src/audio.py` | `start()` に `_resolve_device()` 呼び出し追加、`sd.InputStream(device=)` に渡す |
| `src/ui.py` | `SettingsWindow` にマイク選択セクション追加 |
| `src/main.py` | `_check_mic_on_startup()` 追加・呼び出し |

## Section 1: config.py

### settings.json の変更

```json
{
  "hotkey": "alt",
  "whisper_url": "http://localhost:8001/v1",
  "whisper_model": "deepdml/faster-whisper-large-v3-turbo-ct2",
  "mic_device": null
}
```

- `null`: システムデフォルト（OS の規定録音デバイス）
- 文字列: デバイス名（例: `"Microphone (Blue Yeti)"`）

### 追加メソッド

```python
@classmethod
def get_mic_device(cls) -> str | None:
    config = cls.load_config()
    return config.get("mic_device", None)

@classmethod
def set_mic_device(cls, name: str | None):
    config = cls.load_config()
    config["mic_device"] = name
    cls.save_config(config)
```

`defaults` に `"mic_device": None` を追加する。

## Section 2: audio.py

### start() の変更

```python
def start(self, volume_callback=None):
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

### _resolve_device() ヘルパー

```python
def _resolve_device(self) -> int | None:
    from src.config import ConfigManager
    name = ConfigManager.get_mic_device()
    if name is None:
        return None
    all_devices = sd.query_devices()

    # 完全一致優先
    for i, d in enumerate(all_devices):
        if d['max_input_channels'] > 0 and d['name'] == name:
            return i

    # 部分一致フォールバック（USB ドック経由でポート番号がデバイス名に付与されるケースに対応）
    name_lower = name.lower()
    for i, d in enumerate(all_devices):
        if d['max_input_channels'] > 0 and name_lower in d['name'].lower():
            return i

    print(f"[AudioRecorder] mic '{name}' not found, using default")
    return None
```

**完全一致 → 部分一致の 2 段解決を採用する理由:**
- USB ドック（PC → USB-C → ドック → マイク）経由では、接続ポートが変わると Windows がデバイス名の先頭にポート番号を付加する場合がある（例: `"Microphone (2- Blue Yeti)"`）
- 完全一致で見つからない場合、保存名を部分文字列として検索することで対応する

## Section 3: ui.py

hotkey セクションの直後に Microphone セクションを追加する。スタイルは既存のコンボボックスと統一。

### コンボボックスの初期化

Settings ウィンドウ表示時に `sd.query_devices()` を呼び、`max_input_channels > 0` なデバイス名を列挙する。先頭に `"System Default"` を固定で配置する。

現在の `get_mic_device()` の値に応じて初期選択値をセットする（`None` の場合は `"System Default"`）。

### Apply 時の動作

- `"System Default"` 選択 → `set_mic_device(None)`
- それ以外 → `set_mic_device(selected_name)`
- 成功ダイアログ表示後、ウィンドウを閉じる（hotkey の Apply と同じ挙動）

## main.py: _check_mic_on_startup()

```python
def _check_mic_on_startup(self):
    import sounddevice as sd
    name = ConfigManager.get_mic_device()
    if name is None:
        return
    all_devices = sd.query_devices()
    found = any(
        d['max_input_channels'] > 0 and (
            d['name'] == name or name.lower() in d['name'].lower()
        )
        for d in all_devices
    )
    if not found:
        import tkinter.messagebox
        tkinter.messagebox.showwarning(
            "マイクが見つかりません",
            f"設定されたマイク「{name}」が見つかりません。\nシステムデフォルトを使用します。"
        )
```

`_check_connection_on_startup()` の直後に呼ぶ。

## エラーハンドリング

| シナリオ | 対応 |
|---|---|
| 起動時にマイクが見つからない | 警告ダイアログ表示、その録音セッションはデフォルト使用 |
| 録音中にデバイスエラー | sounddevice の既存エラーハンドリング（`status` コールバック）に委ねる |
| デバイスリストが空 | コンボボックスは `"System Default"` のみ表示 |

## テスト

| テスト | 内容 |
|---|---|
| `test_config.py` | `get_mic_device()` のデフォルト値が `None`、`set_mic_device()` が正しく保存される |
| `test_audio.py` | デバイスが見つかる場合に正しいインデックスを返す、見つからない場合に `None` を返す（`sd.query_devices` をモック） |

## 制約・注意事項

- USB ドックのポート変更で完全一致が外れても部分一致でカバーするが、全く別のポートに移した場合や同名デバイスが複数ある場合は誤マッチの可能性がある（許容範囲として扱う）
- `sd.query_devices()` は同期呼び出しのため、Settings ウィンドウ表示時に一瞬ブロックする可能性があるが、デバイス列挙は高速なため実用上問題ない
