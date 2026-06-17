# Local Speaches Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenAI Whisper API への依存をなくし、ローカルの speaches Docker コンテナ（localhost:8000）を文字起こしバックエンドとして使用する。

**Architecture:** `config.py` に `whisper_url` 設定を追加し、`transcriber.py` が OpenAI クライアントの `base_url` をローカルに向けるよう変更する。起動時に `main.py` が speaches への接続確認を行い、失敗時はポップアップ通知を出す。

**Tech Stack:** Python 3.x, openai SDK (base_url オプション), pytest, unittest.mock

---

## ファイルマップ

| ファイル | 操作 | 内容 |
|---|---|---|
| `src/config.py` | Modify | `whisper_url` のデフォルト値と getter を追加 |
| `src/transcriber.py` | Modify | ローカル base_url に切り替え、`check_connection()` 追加、`reload_key()` 削除 |
| `src/main.py` | Modify | 起動時チェックを接続確認に置き換え、APIキーガード削除 |
| `tests/test_config.py` | Create | `get_whisper_url()` のテスト |
| `tests/test_transcriber.py` | Create | `check_connection()` のテスト |

---

## Task 1: config.py に whisper_url を追加

**Files:**
- Modify: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: tests/ ディレクトリを作成し、失敗するテストを書く**

`tests/__init__.py` を空ファイルで作成。

`tests/test_config.py`:
```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from src.config import ConfigManager

def test_get_whisper_url_returns_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        url = ConfigManager.get_whisper_url()
    assert url == "http://localhost:8000/v1"

def test_get_whisper_url_returns_custom():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={"whisper_url": "http://192.168.1.10:8000/v1"}):
        url = ConfigManager.get_whisper_url()
    assert url == "http://192.168.1.10:8000/v1"
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
cd "C:\Users\kensho\Documents\My Projects\rb10-whisper"
python -m pytest tests/test_config.py -v
```

期待: `AttributeError: type object 'ConfigManager' has no attribute 'get_whisper_url'` で FAIL

- [ ] **Step 3: config.py に実装を追加**

`src/config.py` の `defaults` を変更し、`get_whisper_url()` を追加する。

```python
# load_config() の defaults を以下に変更:
defaults = {"hotkey": "shift", "whisper_url": "http://localhost:8000/v1"}

# クラスの末尾に追加:
@classmethod
def get_whisper_url(cls) -> str:
    """文字起こしバックエンドの URL を取得"""
    config = cls.load_config()
    return config.get("whisper_url", "http://localhost:8000/v1")
```

- [ ] **Step 4: テストを実行して成功を確認**

```
python -m pytest tests/test_config.py -v
```

期待: 2 tests PASSED

- [ ] **Step 5: コミット**

```
git add src/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: config に whisper_url 設定を追加"
```

---

## Task 2: transcriber.py をローカルバックエンドに切り替え

**Files:**
- Modify: `src/transcriber.py`
- Create: `tests/test_transcriber.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_transcriber.py`:
```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python -m pytest tests/test_transcriber.py -v
```

期待: `test_init_uses_local_url` FAIL（現状は `api_key=self.api_key` で呼ばれているため）

- [ ] **Step 3: transcriber.py を書き換える**

`src/transcriber.py` を以下の内容に全面置き換え:

```python
import os
from openai import OpenAI
from src.config import ConfigManager
import re

class Transcriber:
    def __init__(self):
        whisper_url = ConfigManager.get_whisper_url()
        self.client = OpenAI(api_key="dummy", base_url=whisper_url, timeout=30.0)

    def check_connection(self) -> bool:
        """speaches サーバーへの接続確認。成功なら True、失敗なら False を返す。"""
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    def transcribe(self, audio_file_path: str) -> str:
        """音声ファイルをテキストに変換する"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="Systran/faster-whisper-large-v3",
                    file=audio_file,
                    language="ja",
                    prompt="こんにちは。"
                )
            text = transcript.text
            return self._post_process(text)
        except Exception as e:
            print(f"Transcription Error: {e}")
            return ""

    def _post_process(self, text: str) -> str:
        """文字起こし結果のクリーニングと加工。幻覚の除去。"""
        clean_text = re.sub(r'[。\.\,、 \? ！ ！ \n\t]', '', text)
        if len(clean_text) <= 1:
            return ""

        hallucination_phrases = [
            r"ご視聴ありがとうございました",
            r"チャンネル登録お願いします",
            r"高評価お願いします",
            r"おかげさまで",
            r"字幕作成",
            r"視聴してくれてありがとう",
            r"Thank you for watching",
            r"視聴ありがとうございました",
            r"最後までご視聴",
            r"おやすみなさい",
        ]

        for phrase in hallucination_phrases:
            if re.search(f"^{phrase}[。．？！]?$", text) or text == phrase:
                return ""
            text = re.sub(phrase, "", text)

        fillers = [r"えー", r"あー", r"うーん", r"えっと"]
        for filler in fillers:
            text = re.sub(filler, "", text)

        text = text.strip()

        final_clean = re.sub(r'[。\.\,、 \? ！ ！]', '', text)
        if len(final_clean) == 0:
            return ""

        return text
```

- [ ] **Step 4: テストを実行して成功を確認**

```
python -m pytest tests/test_transcriber.py -v
```

期待: 3 tests PASSED

- [ ] **Step 5: コミット**

```
git add src/transcriber.py tests/test_transcriber.py
git commit -m "feat: transcriber をローカル speaches バックエンドに切り替え"
```

---

## Task 3: main.py の起動時チェックを接続確認に置き換え

**Files:**
- Modify: `src/main.py`

テストは UI/起動フローのため手動確認。

- [ ] **Step 1: `_check_api_key_on_startup` を `_check_connection_on_startup` に置き換える**

`main.py` の `_check_api_key_on_startup` メソッドを削除し、以下を追加:

```python
def _check_connection_on_startup(self):
    """起動時に speaches への接続を確認"""
    print("Checking connection to speaches...")
    if not self.transcriber.check_connection():
        print("Warning: speaches is not running.")
        import tkinter.messagebox
        tkinter.messagebox.showwarning(
            "接続エラー",
            "speaches サーバーに接続できません。\n"
            "Docker で whisper-server を起動してください。\n\n"
            "アプリは起動しますが、文字起こしは動作しません。"
        )
    else:
        hotkey = ConfigManager.get_hotkey()
        print(f"Ready to record (Press {hotkey.upper()})")
```

- [ ] **Step 2: `__init__` 内の呼び出しを変更**

`__init__` 内の以下を変更:
```python
# 変更前
self._check_api_key_on_startup()

# 変更後
self._check_connection_on_startup()
```

- [ ] **Step 3: `toggle_recording` の `has_valid_key` ガードを削除**

`toggle_recording` メソッドから以下のブロックを削除:
```python
# 削除するブロック（toggle_recording 内）
if not ConfigManager.has_valid_key():
    self._open_settings()
    return
```

- [ ] **Step 4: `_handle_double_tap` の `has_valid_key` ガードを削除**

`_handle_double_tap` メソッドから以下のブロックを削除:
```python
# 削除するブロック（_handle_double_tap 内）
if not ConfigManager.has_valid_key():
    self._open_settings()
    return
```

- [ ] **Step 5: `_open_settings` の `reload_key` 呼び出しを削除**

`_open_settings` 内の `on_close` コールバックを以下に変更:

```python
def on_close(saved):
    if saved == "hotkey_only":
        self.reload_hotkeys()
        print("Hotkey config updated via settings.")
    elif saved is True:
        self.reload_hotkeys()
        print("Settings saved.")
    else:
        self.reload_hotkeys()
        print("Settings window closed.")
```

- [ ] **Step 6: コミット**

```
git add src/main.py
git commit -m "feat: 起動時チェックを speaches 接続確認に置き換え"
```

---

## Task 4: 動作確認

- [ ] **Step 1: speaches コンテナを起動**

```
docker start whisper-server
```

- [ ] **Step 2: speaches API が応答するか確認**

```
curl http://localhost:8000/v1/models
```

期待: JSON でモデル一覧が返ってくる（`Systran/faster-whisper-large-v3` が含まれる）

- [ ] **Step 3: アプリを起動して動作確認**

```
cd "C:\Users\kensho\Documents\My Projects\rb10-whisper"
python launcher.py
```

確認項目:
- ターミナルに `Ready to record (Press SHIFT)` と出ること
- ホットキーを押して録音・文字起こしが動くこと
- 文字起こし結果がカーソル位置にペーストされること

- [ ] **Step 4: 接続エラー時の挙動確認**

```
docker stop whisper-server
python launcher.py
```

確認項目:
- 警告ダイアログが表示されること
- アプリが起動し続けること（クラッシュしないこと）

- [ ] **Step 5: 全テストを実行**

```
python -m pytest tests/ -v
```

期待: 全テスト PASS

- [ ] **Step 6: 最終コミット**

```
git add -A
git commit -m "test: 動作確認完了"
```
