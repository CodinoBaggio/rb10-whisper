# コンビネーションホットキー — 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ホットキーを「修飾キー+任意キー」の組み合わせに変更し、Hold（押している間録音）と Toggle（押すたびにオン/オフ）を別々のキーコンボで設定できるようにする

**Architecture:** ConfigManager に `parse_hotkey()` と `get/set_hotkey_toggle()` を追加し、main.py の `_on_key_event` を Hold/Toggle の2コンボ検出に書き換える。Settings UI の Hotkey セクションを Hold/Toggle 2行のキャプチャ式 UI に差し替える。ダブルタップロジックは完全削除。

**Tech Stack:** Python 3.11, Tkinter, keyboard ライブラリ, src/config.py, src/main.py, src/ui.py, tests/test_config.py

---

## ファイル構成

| ファイル | 変更内容 |
|---|---|
| `src/config.py` | `parse_hotkey()` 追加、`get_hotkey_toggle()` / `set_hotkey_toggle()` 追加、デフォルト値更新 |
| `src/main.py` | `reload_hotkeys()` 書き換え、`_on_key_event()` 書き換え、`_handle_toggle()` 追加、`_set_capturing()` 追加、ダブルタップ削除、`_open_settings()` 更新 |
| `src/ui.py` | Hotkey セクション差し替え（Hold/Toggle 2行）、`_capture_key()` 追加、`_apply_hotkey()` 書き換え、コンストラクタに `suspend_callback` 追加 |
| `tests/test_config.py` | `parse_hotkey()` のテスト3件、`get/set_hotkey_toggle()` のテスト2件 追加 |

---

## Task 1: ConfigManager — parse_hotkey / get_hotkey_toggle / set_hotkey_toggle (TDD)

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_config.py` の末尾に追加:

```python
def test_parse_hotkey_returns_modifier_and_key():
    modifier, key = ConfigManager.parse_hotkey("ctrl+x")
    assert modifier == "ctrl"
    assert key == "x"


def test_parse_hotkey_handles_multichar_key():
    modifier, key = ConfigManager.parse_hotkey("alt+space")
    assert modifier == "alt"
    assert key == "space"


def test_parse_hotkey_returns_empty_for_old_format():
    modifier, key = ConfigManager.parse_hotkey("alt")
    assert modifier == ""
    assert key == ""


def test_get_hotkey_toggle_returns_default():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'load_config', return_value={}):
        toggle = ConfigManager.get_hotkey_toggle()
    assert toggle == "alt+z"


def test_set_hotkey_toggle_saves_value(tmp_path, monkeypatch):
    ConfigManager._config_cache = None
    monkeypatch.setenv("APPDATA", str(tmp_path))
    ConfigManager.set_hotkey_toggle("ctrl+q")
    ConfigManager._config_cache = None
    assert ConfigManager.get_hotkey_toggle() == "ctrl+q"
```

- [ ] **Step 2: テストが失敗することを確認**

```
cd "C:\Users\kensho\Documents\My Projects\rb10-whisper"
python -m pytest tests/test_config.py::test_parse_hotkey_returns_modifier_and_key tests/test_config.py::test_get_hotkey_toggle_returns_default -v
```

期待: `AttributeError: type object 'ConfigManager' has no attribute 'parse_hotkey'` で FAILED

- [ ] **Step 3: 実装を追加**

`src/config.py` の `get_hotkey()` メソッドの直前に `parse_hotkey` を追加し、`get_whisper_url()` の後に `get_hotkey_toggle` / `set_hotkey_toggle` を追加する。また `load_config()` のデフォルト値を更新する。

**`load_config()` の defaults dict を更新** (既存の `"hotkey": "shift"` と `"whisper_url": ...` の行):

```python
        defaults = {
            "hotkey": "alt+x",
            "hotkey_toggle": "alt+z",
            "whisper_url": "http://localhost:8000/v1",
            "whisper_model": "Systran/faster-whisper-large-v3",
            "mic_device": None
        }
```

**`get_hotkey()` メソッドの直前に追加**:

```python
    @classmethod
    def parse_hotkey(cls, hotkey_str: str) -> tuple[str, str]:
        """`"ctrl+x"` → `("ctrl", "x")`. `+` がない旧フォーマットは `("", "")` を返す"""
        if "+" not in hotkey_str:
            return ("", "")
        parts = hotkey_str.split("+", 1)
        return (parts[0].lower(), parts[1].lower())

```

**`set_whisper_url()` の直後に追加**:

```python
    @classmethod
    def get_hotkey_toggle(cls) -> str:
        """トグル録音のホットキーを取得"""
        config = cls.load_config()
        return config.get("hotkey_toggle", "alt+z")

    @classmethod
    def set_hotkey_toggle(cls, hotkey: str) -> None:
        """トグル録音のホットキーを保存"""
        config = cls.load_config()
        config["hotkey_toggle"] = hotkey
        cls.save_config(config)

```

- [ ] **Step 4: テストが通ることを確認**

```
python -m pytest tests/test_config.py -v
```

期待: 13テスト全て PASSED（既存8 + 新規5）

- [ ] **Step 5: コミット**

```
git add src/config.py tests/test_config.py
git commit -m "feat: add parse_hotkey and hotkey_toggle support to ConfigManager"
```

---

## Task 2: main.py — ホットキーロジック書き換え

**Files:**
- Modify: `src/main.py`

このタスクでは UI 変更なしに main.py のホットキー検出ロジックだけを書き換える。Settings からの `suspend_callback` も追加する。

- [ ] **Step 1: `__init__` のホットキー関連インスタンス変数を差し替える**

`AudioInputApp.__init__` の以下のブロック:

```python
        # ホットキー設定
        # keyboardライブラリを使用し、修飾キーの干渉を防ぐ独自ロジックを実装
        self._hotkey_name = ""
        self._key_held = False
        self._is_toggled = False
        self._last_press_time = 0
        self._other_key_pressed_during_hold = False
        self._hold_timer = None
```

を以下に差し替える:

```python
        # ホットキー設定
        self._modifier_hold   = ""
        self._trigger_hold    = ""
        self._modifier_toggle = ""
        self._trigger_toggle  = ""
        self._capturing       = False
        self._key_held        = False
        self._is_toggled      = False
        self._other_key_pressed_during_hold = False
        self._hold_timer      = None
```

- [ ] **Step 2: `reload_hotkeys()` を書き換える**

既存の `reload_hotkeys()` メソッド全体を以下に差し替える:

```python
    def reload_hotkeys(self):
        """ホットキーを再登録する"""
        try:
            keyboard.unhook_all()
            hold_str   = ConfigManager.get_hotkey()
            toggle_str = ConfigManager.get_hotkey_toggle()

            mod_h, trg_h = ConfigManager.parse_hotkey(hold_str)
            mod_t, trg_t = ConfigManager.parse_hotkey(toggle_str)

            # 旧フォーマット（+ なし）のフォールバック
            if not trg_h:
                mod_h, trg_h = "alt", "x"
            if not trg_t:
                mod_t, trg_t = "alt", "z"

            self._modifier_hold   = mod_h
            self._trigger_hold    = trg_h
            self._modifier_toggle = mod_t
            self._trigger_toggle  = trg_t

            keyboard.hook(self._on_key_event)
            print(f"Hotkeys registered. Hold: [{mod_h.upper()}+{trg_h.upper()}], Toggle: [{mod_t.upper()}+{trg_t.upper()}]")
        except Exception as e:
            msg = f"Failed to register hotkeys: {e}"
            print(msg)
            log_error(msg)
```

- [ ] **Step 3: `_on_key_event()` を書き換える**

既存の `_on_key_event()` メソッド全体を以下に差し替える:

```python
    def _on_key_event(self, event):
        """全てのキーイベントを監視し、Hold/Toggle コンボを検出する"""
        if self._capturing:
            return

        name = event.name.lower()

        # ESC キャンセル
        if name == "esc" and event.event_type == keyboard.KEY_DOWN:
            self.root.after(0, self.cancel_recording)
            return

        is_hold_key   = (name == self._trigger_hold)   and keyboard.is_pressed(self._modifier_hold)
        is_toggle_key = (name == self._trigger_toggle) and keyboard.is_pressed(self._modifier_toggle)

        if event.event_type == keyboard.KEY_DOWN:
            if is_hold_key:
                if not self._key_held:
                    self._key_held = True
                    self._other_key_pressed_during_hold = False
                    if self._hold_timer:
                        self.root.after_cancel(self._hold_timer)
                    self._hold_timer = self.root.after(300, self._check_hold_start)
            elif is_toggle_key:
                self.root.after(0, self._handle_toggle)
            elif self._key_held and name != self._modifier_hold:
                self._other_key_pressed_during_hold = True

        elif event.event_type == keyboard.KEY_UP:
            if is_hold_key:
                self._key_held = False
                if self.is_recording and not self._is_toggled:
                    self.root.after(0, self.stop_and_transcribe)
```

- [ ] **Step 4: `_handle_double_tap()` を削除し `_handle_toggle()` を追加する**

`_handle_double_tap()` メソッドを丸ごと削除し、その場所に以下を追加:

```python
    def _handle_toggle(self):
        """Toggle キー押下時: 録音中なら停止、停止中なら開始"""
        if self.is_recording:
            self._is_toggled = False
            self.stop_and_transcribe()
        elif not self.processing:
            self._is_toggled = True
            self.start_recording()
```

- [ ] **Step 5: `_set_capturing()` を追加する**

`_handle_toggle()` の直後に追加:

```python
    def _set_capturing(self, flag: bool) -> None:
        """キーキャプチャ中フラグを設定する（Settings UI から呼ばれる）"""
        self._capturing = flag
```

- [ ] **Step 6: `_open_settings()` に `suspend_callback` を渡す**

`_open_settings()` 内の `SettingsWindow(...)` 呼び出しを以下に変更:

```python
        SettingsWindow(self.root, on_close_callback=on_close, suspend_callback=self._set_capturing)
```

- [ ] **Step 7: 全テストが通ることを確認**

```
python -m pytest tests/ -v
```

期待: 18テスト全て PASSED（test_config.py の `get_hotkey` 系テストが既存のまま通ること確認）

- [ ] **Step 8: コミット**

```
git add src/main.py
git commit -m "feat: combo hotkey detection in main.py (Hold/Toggle, remove double-tap)"
```

---

## Task 3: Settings UI — Hotkey セクション差し替え

**Files:**
- Modify: `src/ui.py`

- [ ] **Step 1: `SettingsWindow.__init__` に `suspend_callback` 引数を追加**

```python
    def __init__(self, root, on_close_callback=None, suspend_callback=None):
        self.root = root
        self.on_close_callback = on_close_callback
        self.suspend_callback = suspend_callback
```

既存の `def __init__(self, root, on_close_callback=None):` と `self.on_close_callback = on_close_callback` の2行を上記に差し替える。

- [ ] **Step 2: `_setup_ui()` 内の Hotkey セクションを差し替える**

既存の Hotkey セクション（`# ホットキー設定コンテナ` から `lbl_hotkey_desc.pack(anchor='w')` まで）を以下に差し替える:

```python
        # ホットキー設定コンテナ
        hotkey_container = tk.Frame(self.window, padx=20, pady=10, bg=bg_color)
        hotkey_container.pack(fill='x')

        tk.Label(hotkey_container, text="Recording Hotkey:", bg=bg_color, fg=fg_color).pack(anchor='w')

        modifier_options = ["Ctrl", "Alt"]

        # --- Hold キー行 ---
        tk.Label(hotkey_container, text="Hold (押している間録音):",
                 bg=bg_color, fg=fg_color, font=("Helvetica", 9)).pack(anchor='w')
        hold_row = tk.Frame(hotkey_container, bg=bg_color)
        hold_row.pack(fill='x', pady=(2, 5))

        hold_str = ConfigManager.get_hotkey()
        hold_mod, hold_key = ConfigManager.parse_hotkey(hold_str)
        if not hold_key:
            hold_mod, hold_key = "alt", "x"

        self.hold_modifier_var = tk.StringVar(value=hold_mod.capitalize())
        self.hold_key_var      = tk.StringVar(value=hold_key)

        self.hold_modifier_combo = ttk.Combobox(hold_row, textvariable=self.hold_modifier_var,
                                                 values=modifier_options, state="readonly", width=6)
        self.hold_modifier_combo.pack(side=tk.LEFT)

        tk.Label(hold_row, text="+", bg=bg_color, fg=fg_color).pack(side=tk.LEFT, padx=4)

        self.hold_key_entry = tk.Entry(hold_row, textvariable=self.hold_key_var,
                                       bg="#333333", fg="white", insertbackground="white",
                                       relief=tk.FLAT, width=8, state="readonly")
        self.hold_key_entry.pack(side=tk.LEFT, ipady=3)

        self.btn_capture_hold = tk.Button(hold_row, text="Press key...",
                                          command=lambda: self._capture_key("hold"),
                                          bg="#444444", fg="white", activebackground="#555555",
                                          relief=tk.FLAT, font=("Helvetica", 9), cursor="hand2")
        self.btn_capture_hold.pack(side=tk.LEFT, padx=(8, 0))

        # --- Toggle キー行 ---
        tk.Label(hotkey_container, text="Toggle (押すたびにオン/オフ):",
                 bg=bg_color, fg=fg_color, font=("Helvetica", 9)).pack(anchor='w')
        toggle_row = tk.Frame(hotkey_container, bg=bg_color)
        toggle_row.pack(fill='x', pady=(2, 5))

        toggle_str = ConfigManager.get_hotkey_toggle()
        toggle_mod, toggle_key = ConfigManager.parse_hotkey(toggle_str)
        if not toggle_key:
            toggle_mod, toggle_key = "alt", "z"

        self.toggle_modifier_var = tk.StringVar(value=toggle_mod.capitalize())
        self.toggle_key_var      = tk.StringVar(value=toggle_key)

        self.toggle_modifier_combo = ttk.Combobox(toggle_row, textvariable=self.toggle_modifier_var,
                                                   values=modifier_options, state="readonly", width=6)
        self.toggle_modifier_combo.pack(side=tk.LEFT)

        tk.Label(toggle_row, text="+", bg=bg_color, fg=fg_color).pack(side=tk.LEFT, padx=4)

        self.toggle_key_entry = tk.Entry(toggle_row, textvariable=self.toggle_key_var,
                                         bg="#333333", fg="white", insertbackground="white",
                                         relief=tk.FLAT, width=8, state="readonly")
        self.toggle_key_entry.pack(side=tk.LEFT, ipady=3)

        self.btn_capture_toggle = tk.Button(toggle_row, text="Press key...",
                                            command=lambda: self._capture_key("toggle"),
                                            bg="#444444", fg="white", activebackground="#555555",
                                            relief=tk.FLAT, font=("Helvetica", 9), cursor="hand2")
        self.btn_capture_toggle.pack(side=tk.LEFT, padx=(8, 0))

        # --- Apply ボタン行 ---
        apply_hotkey_row = tk.Frame(hotkey_container, bg=bg_color)
        apply_hotkey_row.pack(fill='x', pady=(0, 5))

        self.btn_apply_hotkey = tk.Button(apply_hotkey_row, text="Apply Hotkey",
                                          command=self._apply_hotkey,
                                          bg=btn_bg, fg="white", activebackground=btn_active,
                                          relief=tk.FLAT, width=12,
                                          font=("Helvetica", 10, "bold"), cursor="hand2")
        self.btn_apply_hotkey.pack(side=tk.RIGHT)

        lbl_hotkey_desc = tk.Label(hotkey_container,
                                   text="設定を変更したら「Apply Hotkey」を押してください",
                                   bg=bg_color, fg="#aaaaaa", font=("Helvetica", 9),
                                   justify=tk.LEFT)
        lbl_hotkey_desc.pack(anchor='w')
```

- [ ] **Step 3: `_capture_key()` メソッドを追加する**

`_apply_hotkey()` の直前に以下を挿入:

```python
    _MODIFIER_NAMES = {
        "ctrl", "alt", "shift", "win",
        "left ctrl", "right ctrl", "left alt", "right alt",
        "left shift", "right shift", "left windows", "right windows",
        "caps lock", "num lock", "scroll lock", "menu",
    }

    def _capture_key(self, target: str) -> None:
        """'hold' または 'toggle' のキャプチャを開始する"""
        if target == "hold":
            btn     = self.btn_capture_hold
            key_var = self.hold_key_var
        else:
            btn     = self.btn_capture_toggle
            key_var = self.toggle_key_var

        if btn.cget("text") == "Waiting...":
            return  # すでにキャプチャ中

        prev_value = key_var.get()
        if self.suspend_callback:
            self.suspend_callback(True)

        btn.config(text="Waiting...", state="disabled", bg="#886600")

        hook_ref    = [None]
        timeout_ref = [None]

        def finish(key_name: str) -> None:
            if hook_ref[0] is not None:
                keyboard.unhook(hook_ref[0])
                hook_ref[0] = None
            if timeout_ref[0] is not None:
                self.window.after_cancel(timeout_ref[0])
                timeout_ref[0] = None
            key_var.set(key_name)
            btn.config(text="Press key...", state="normal", bg="#444444")
            if self.suspend_callback:
                self.suspend_callback(False)

        def on_key(event) -> None:
            if event.event_type != keyboard.KEY_DOWN:
                return
            name = event.name.lower()
            if name in self._MODIFIER_NAMES:
                return
            self.window.after(0, lambda: finish(name))

        def on_timeout() -> None:
            self.window.after(0, lambda: finish(prev_value))

        hook_ref[0]    = keyboard.hook(on_key)
        timeout_ref[0] = self.window.after(10000, on_timeout)
```

- [ ] **Step 4: `_apply_hotkey()` を書き換える**

既存の `_apply_hotkey()` メソッド全体を以下に差し替える:

```python
    def _apply_hotkey(self):
        """Hold / Toggle ホットキーを保存してリロードをトリガーする"""
        hold_mod   = self.hold_modifier_var.get().lower()
        hold_key   = self.hold_key_var.get().strip()
        toggle_mod = self.toggle_modifier_var.get().lower()
        toggle_key = self.toggle_key_var.get().strip()

        if not hold_key:
            messagebox.showerror("Error", "Hold キーが設定されていません。")
            return
        if not toggle_key:
            messagebox.showerror("Error", "Toggle キーが設定されていません。")
            return

        self._set_cursor("watch")

        def task():
            try:
                ConfigManager.set_hotkey(f"{hold_mod}+{hold_key}")
                ConfigManager.set_hotkey_toggle(f"{toggle_mod}+{toggle_key}")
                label = (f"Hold: {hold_mod.upper()}+{hold_key.upper()}, "
                         f"Toggle: {toggle_mod.upper()}+{toggle_key.upper()}")
                self.window.after(0, lambda: self._on_save_completed(f"Hotkey applied!\n{label}"))
                if self.on_close_callback:
                    self.window.after(0, lambda: self.on_close_callback("hotkey_only"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Error", f"Failed to apply hotkey: {e}"))
            finally:
                self.window.after(0, lambda: self._set_cursor(""))

        threading.Thread(target=task, daemon=True).start()
```

- [ ] **Step 5: 全テストが通ることを確認**

```
python -m pytest tests/ -v
```

期待: 全テスト PASSED（18テスト）

- [ ] **Step 6: 手動確認**

```
python launcher.py
```

確認項目:
- Settings を開く → Hotkey セクションが Hold / Toggle の2行になっていること
- "Press key..." を押すと "Waiting..." になり、任意のキーを押すと Entry に表示されること
- Apply Hotkey → settings.json に `"hotkey": "alt+x"`, `"hotkey_toggle": "alt+z"` が保存されていること
- Alt+X を長押しで録音開始、離すと停止すること
- Alt+Z を押すと録音開始、もう一度押すと停止すること
- ESC で録音キャンセルできること

- [ ] **Step 7: コミット**

```
git add src/ui.py
git commit -m "feat: combo hotkey Settings UI with key capture for Hold and Toggle"
```
