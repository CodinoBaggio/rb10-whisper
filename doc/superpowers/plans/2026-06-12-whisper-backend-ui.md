# Whisper バックエンド設定 UI — 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Settings 画面から `whisper_url` と `whisper_model` を変更できる Backend セクションを追加し、localhost 時にはモデル一覧を API から取得して Combobox で選択できるようにする

**Architecture:** ConfigManager に setter 2つを追加し、SettingsWindow の `_setup_ui()` に Backend セクションを挿入する。URL Entry の FocusOut イベントと画面起動時に localhost 判定を行い、一致すれば `urllib.request` でバックグラウンドフェッチしてモデル Combobox に切り替える。外部 URL または取得失敗時は Entry にフォールバックする。

**Tech Stack:** Python 3.11, Tkinter (ttk.Combobox / tk.Entry), urllib.request (stdlib), src/config.py, src/ui.py, tests/test_config.py

---

## ファイル構成

| ファイル | 変更内容 |
|---|---|
| `src/config.py` | `set_whisper_url()` / `set_whisper_model()` を追加 |
| `src/ui.py` | Backend セクション追加、動的ウィジェット切り替え、Apply ロジック、ウィンドウ高さ変更 |
| `tests/test_config.py` | setter 2つのテストを追加 |

---

## Task 1: ConfigManager に set_whisper_url / set_whisper_model を追加 (TDD)

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_config.py` の末尾に追加:

```python
def test_set_whisper_url_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_whisper_url("http://192.168.1.100:8001/v1")
    ConfigManager._config_cache = None
    assert ConfigManager.get_whisper_url() == "http://192.168.1.100:8001/v1"


def test_set_whisper_model_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_whisper_model("openai/whisper-large-v3")
    ConfigManager._config_cache = None
    assert ConfigManager.get_whisper_model() == "openai/whisper-large-v3"
```

- [ ] **Step 2: テストが失敗することを確認**

```
cd "C:\Users\kensho\Documents\My Projects\rb10-whisper"
python -m pytest tests/test_config.py::test_set_whisper_url_saves_value tests/test_config.py::test_set_whisper_model_saves_value -v
```

期待: `AttributeError: type object 'ConfigManager' has no attribute 'set_whisper_url'` で FAILED

- [ ] **Step 3: 実装を追加**

`src/config.py` の `get_whisper_model()` の直後（`get_mic_device()` の前）に追加:

```python
    @classmethod
    def set_whisper_url(cls, url: str) -> None:
        config = cls.load_config()
        config["whisper_url"] = url
        cls.save_config(config)

    @classmethod
    def set_whisper_model(cls, model: str) -> None:
        config = cls.load_config()
        config["whisper_model"] = model
        cls.save_config(config)
```

- [ ] **Step 4: テストが通ることを確認**

```
python -m pytest tests/test_config.py -v
```

期待: 8テスト全て PASSED

- [ ] **Step 5: コミット**

```
git add src/config.py tests/test_config.py
git commit -m "feat: add set_whisper_url and set_whisper_model to ConfigManager"
```

---

## Task 2: Backend UI セクション（静的レイアウト + Apply ボタン）

**Files:**
- Modify: `src/ui.py`

このタスクでは動的フェッチなしの静的レイアウトを作る。モデルフィールドは常に Entry として配置する。

- [ ] **Step 1: ウィンドウ高さを変更**

`src/ui.py` の `_setup_ui()` 冒頭付近（`self.window.geometry("800x500")` の行）を変更:

```python
        self.window.geometry("800x700")
```

- [ ] **Step 2: Backend セクションを追加**

`src/ui.py` の `_setup_ui()` 内の Hotkey セクションブロック（`lbl_hotkey_desc.pack(anchor='w')` 行）の直後、かつ `# マイク選択コンテナ` の前に追加:

```python
        # バックエンド設定コンテナ
        backend_container = tk.Frame(self.window, padx=20, pady=10, bg=bg_color)
        backend_container.pack(fill='x')

        tk.Label(backend_container, text="Backend:", bg=bg_color, fg=fg_color).pack(anchor='w')

        # URL 入力行
        tk.Label(backend_container, text="Whisper URL:",
                 bg=bg_color, fg=fg_color, font=("Helvetica", 9)).pack(anchor='w')
        url_row = tk.Frame(backend_container, bg=bg_color)
        url_row.pack(fill='x', pady=(2, 5))

        self.url_var = tk.StringVar(value=ConfigManager.get_whisper_url())
        self.url_entry = tk.Entry(url_row, textvariable=self.url_var,
                                  bg="#333333", fg="white",
                                  insertbackground="white", relief=tk.FLAT)
        self.url_entry.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)

        # モデル入力行
        tk.Label(backend_container, text="Model:",
                 bg=bg_color, fg=fg_color, font=("Helvetica", 9)).pack(anchor='w')
        self.model_row = tk.Frame(backend_container, bg=bg_color)
        self.model_row.pack(fill='x', pady=(2, 5))

        self.model_var = tk.StringVar(value=ConfigManager.get_whisper_model())
        self.model_widget = tk.Entry(self.model_row, textvariable=self.model_var,
                                     bg="#333333", fg="white",
                                     insertbackground="white", relief=tk.FLAT)
        self.model_widget.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)

        # Apply ボタン行
        apply_backend_row = tk.Frame(backend_container, bg=bg_color)
        apply_backend_row.pack(fill='x', pady=(0, 5))

        self.btn_apply_backend = tk.Button(
            apply_backend_row, text="Apply Backend",
            command=self._apply_backend,
            bg=btn_bg, fg="white", activebackground=btn_active,
            relief=tk.FLAT, width=14,
            font=("Helvetica", 10, "bold"), cursor="hand2"
        )
        self.btn_apply_backend.pack(side=tk.RIGHT)

        tk.Label(backend_container,
                 text="設定を変更したら「Apply Backend」を押してください",
                 bg=bg_color, fg="#aaaaaa", font=("Helvetica", 9),
                 justify=tk.LEFT).pack(anchor='w')
```

- [ ] **Step 3: `_apply_backend()` メソッドを追加**

`src/ui.py` の `_apply_mic()` メソッドの直後に追加:

```python
    def _apply_backend(self):
        """バックエンド URL とモデルを保存"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Whisper URL is empty.")
            return
        if not url.startswith("http"):
            messagebox.showerror("Error", "Whisper URL must start with 'http'.")
            return

        model = self.model_var.get().strip()
        if not model or model == "Fetching...":
            messagebox.showerror("Error", "Model is empty or still loading.")
            return

        self._set_cursor("watch")

        def task():
            try:
                ConfigManager.set_whisper_url(url)
                ConfigManager.set_whisper_model(model)
                self.window.after(0, lambda: self._on_save_completed(f"Backend [{url}] applied!"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", f"Failed to apply backend: {e}"))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))

        threading.Thread(target=task, daemon=True).start()
```

- [ ] **Step 4: 手動で動作確認**

```
python -m src.main
```

- Settings を開く → Backend セクション（URL・Model 入力欄 + Apply Backend ボタン）が表示されること
- URL / Model を変更して Apply Backend → `%APPDATA%\rb10-whisper\settings.json` に反映されていること
- 空 URL → エラーダイアログが出ること
- `http` 以外で始まる URL → エラーダイアログが出ること

- [ ] **Step 5: コミット**

```
git add src/ui.py
git commit -m "feat: add Backend UI section with URL/model entry and Apply button"
```

---

## Task 3: 動的モデルフェッチ（localhost 判定 + Combobox 切り替え）

**Files:**
- Modify: `src/ui.py`

- [ ] **Step 1: ヘルパーメソッドを追加**

`src/ui.py` の `_apply_backend()` の直後に以下4つのメソッドを追加:

```python
    def _is_localhost_url(self, url: str) -> bool:
        return "localhost" in url or "127.0.0.1" in url

    def _start_model_fetch(self, url: str) -> None:
        """バックグラウンドでモデル一覧を取得する"""
        self._prefetch_model_value = self.model_var.get()
        self.model_var.set("Fetching...")
        self.model_widget.config(state="disabled")
        threading.Thread(
            target=self._fetch_models_async, args=(url,), daemon=True
        ).start()

    def _fetch_models_async(self, url: str) -> None:
        """バックグラウンドスレッドで /v1/models を取得し、結果をメインスレッドへ渡す"""
        import urllib.request
        import json as _json
        models_url = url.rstrip("/") + "/models"
        try:
            with urllib.request.urlopen(models_url, timeout=5) as resp:
                data = _json.loads(resp.read().decode())
            models = [item["id"] for item in data.get("data", [])]
            if models:
                self.window.after(0, lambda: self._switch_to_model_combo(models))
                return
        except Exception:
            pass
        restore = getattr(self, '_prefetch_model_value', ConfigManager.get_whisper_model())
        self.window.after(0, lambda: self._switch_to_model_entry(restore))

    def _switch_to_model_combo(self, models: list) -> None:
        """モデルウィジェットを Combobox（選択式）に切り替える"""
        current = self.model_var.get()
        initial = current if current in models else models[0]
        self.model_widget.destroy()
        self.model_var.set(initial)
        self.model_widget = ttk.Combobox(
            self.model_row, textvariable=self.model_var,
            values=models, state="readonly"
        )
        self.model_widget.pack(side=tk.LEFT, fill='x', expand=True, ipady=3)

    def _switch_to_model_entry(self, restore_value: str | None = None) -> None:
        """モデルウィジェットを Entry（手入力）に切り替える"""
        current = self.model_var.get()
        value = restore_value if restore_value is not None else (
            ConfigManager.get_whisper_model() if current == "Fetching..." else current
        )
        if isinstance(self.model_widget, ttk.Combobox):
            self.model_widget.destroy()
            self.model_widget = tk.Entry(
                self.model_row, textvariable=self.model_var,
                bg="#333333", fg="white",
                insertbackground="white", relief=tk.FLAT
            )
            self.model_widget.pack(side=tk.LEFT, fill='x', expand=True, ipady=5)
        else:
            self.model_widget.config(state="normal")
        self.model_var.set(value)
```

- [ ] **Step 2: URL Entry に FocusOut イベントをバインド**

Task 2 の Step 2 で追加した `self.url_entry.pack(...)` 行の直後に追加:

```python
        self.url_entry.bind("<FocusOut>", self._on_url_blur)
```

そして `_apply_backend()` の直前に `_on_url_blur` メソッドを追加:

```python
    def _on_url_blur(self, event) -> None:
        """URL 欄からフォーカスが外れたときにモデルウィジェットを切り替える"""
        url = self.url_var.get().strip()
        if self._is_localhost_url(url):
            self._start_model_fetch(url)
        else:
            self._switch_to_model_entry()
```

- [ ] **Step 3: Settings 起動時に初回フェッチをトリガー**

`src/ui.py` の `_setup_ui()` の末尾（`self.btn_close.pack(side=tk.RIGHT)` の後）に追加:

```python
        # 起動時に URL が localhost なら即フェッチ
        initial_url = ConfigManager.get_whisper_url()
        if self._is_localhost_url(initial_url):
            self.window.after(200, lambda: self._start_model_fetch(initial_url))
```

- [ ] **Step 4: 手動で動作確認**

以下のシナリオを順に確認する:

**シナリオ A: speaches 起動中**
```
docker start whisper-turbo   # speaches を起動
python -m src.main
```
- Settings を開く → Model フィールドに "Fetching..." が一瞬表示され、Combobox に切り替わること
- Combobox にモデル一覧が入っていること
- config に保存済みのモデルが選択されていること

**シナリオ B: speaches 停止中**
```
docker stop whisper-turbo
python -m src.main
```
- Settings を開く → フェッチ失敗 → Entry にフォールバック、config のモデル名が表示されること

**シナリオ C: URL を外部に変えて blur**
- URL 欄を `http://api.example.com/v1` に変更してフォーカスを外す → Model が Entry に切り替わること

**シナリオ D: 外部 URL → localhost に戻して blur**
- URL を `http://localhost:8001/v1` に戻してフォーカスを外す → Combobox に切り替わること（speaches 起動時）

- [ ] **Step 5: 全自動テストが通ることを確認**

```
python -m pytest tests/ -v
```

期待: 全テスト PASSED

- [ ] **Step 6: コミット**

```
git add src/ui.py
git commit -m "feat: dynamic model combobox via localhost fetch in Backend section"
```
