# コンビネーションホットキー — 設計仕様

**日付:** 2026-06-12
**対象ブランチ:** feature/local-speaches-backend
**スコープ:** ホットキーを「単一キー長押し」から「修飾キー+任意キー」の組み合わせに変更し、Hold / Toggle を別々に設定可能にする

---

## 背景と目的

現在のホットキーは Alt 等の単一キーの長押しで録音を開始する。修飾キー（Ctrl / Alt）と任意のキーの組み合わせで起動できるようにし、他アプリとのショートカット衝突を回避しやすくする。ダブルタップによるトグルを廃止し、代わりに Hold / Toggle を独立したキーコンボで制御する。

---

## 設定フォーマット

`settings.json` に以下2キーを持つ:

```json
{
  "hotkey":        "alt+x",
  "hotkey_toggle": "alt+z"
}
```

- `hotkey` — Hold キー: 押している間だけ録音する
- `hotkey_toggle` — Toggle キー: 押すたびに録音オン/オフを切り替える
- フォーマット: `"<modifier>+<key>"` の文字列（小文字）
- modifier の選択肢: `ctrl` / `alt`
- `+` を含まない旧フォーマット（例: `"alt"`）が保存されている場合は、それぞれのデフォルト値を使用する

**デフォルト値:**
- `hotkey`: `"alt+x"`
- `hotkey_toggle`: `"alt+z"`

---

## ConfigManager の変更

`src/config.py` に追加するメソッド:

```python
@classmethod
def parse_hotkey(cls, hotkey_str: str) -> tuple[str, str]:
    """
    "ctrl+x" → ("ctrl", "x")
    旧フォーマット（"alt" など + なし）は ("", "") を返す
    """
    if "+" not in hotkey_str:
        return ("", "")
    parts = hotkey_str.split("+", 1)
    return (parts[0].lower(), parts[1].lower())

@classmethod
def get_hotkey_toggle(cls) -> str:
    config = cls.load_config()
    return config.get("hotkey_toggle", "alt+z")

@classmethod
def set_hotkey_toggle(cls, hotkey: str) -> None:
    config = cls.load_config()
    config["hotkey_toggle"] = hotkey
    cls.save_config(config)
```

`load_config()` のデフォルト値を更新:

```python
defaults = {
    "hotkey":        "alt+x",   # 変更
    "hotkey_toggle": "alt+z",   # 追加
    ...
}
```

---

## Settings UI の変更

`src/ui.py` の Hotkey セクションを以下に差し替える:

```
Recording Hotkey:
  Hold (押している間録音):
    [ Alt ▼ ] + [ x ] [Press key...]

  Toggle (押すたびにオン/オフ):
    [ Alt ▼ ] + [ z ] [Press key...]

  [Apply Hotkey]
  設定を変更したら「Apply Hotkey」を押してください
```

### ウィジェット構成

Hold / Toggle それぞれに:
- Modifier Combobox: `["Ctrl", "Alt"]`（readonly）
- Key Entry: 現在のトリガーキー名を表示（`state="readonly"` — キャプチャ専用、手入力不可）
- "Press key..." ボタン: クリックするとキャプチャモード開始

### キャプチャ動作

1. "Press key..." ボタンを押すと `_capturing = True`（`AudioInputApp` の録音ロジック停止フラグ）をセット
2. ボタンテキストを "Waiting..." に変更、ボタンを disable
3. `keyboard.hook` で次のキーイベントを待ち受け（既存フックとは別に追加）
4. Ctrl / Alt / Shift / Win / Menu などの修飾キー単体は無視
5. 最初の非修飾キー押下を取得:
   - Key Entry に `event.name.lower()` を表示
   - フックを解除
   - ボタンを "Press key..." に戻し、enable
   - `_capturing = False`
6. 10秒タイムアウト: キャプチャ中止、元の値に戻す、`_capturing = False`

### Apply Hotkey

`_apply_hotkey()` を変更:
- Hold: `modifier_hold + "+" + trigger_hold` を `ConfigManager.set_hotkey()` で保存
- Toggle: `modifier_toggle + "+" + trigger_toggle` を `ConfigManager.set_hotkey_toggle()` で保存
- どちらかが未入力（key が空）の場合は `messagebox.showerror` でブロック
- 保存後は `on_close_callback("hotkey_only")` を呼び `reload_hotkeys()` をトリガー

### AudioInputApp への suspend コールバック

`SettingsWindow` のコンストラクタに `suspend_callback` を追加:

```python
SettingsWindow(root, on_close_callback=..., suspend_callback=self._set_capturing)
```

`AudioInputApp._set_capturing(flag: bool)` — `self._capturing` を設定する。

---

## main.py の変更

### インスタンス変数

```python
self._modifier_hold   = ""   # 例: "alt"
self._trigger_hold    = ""   # 例: "x"
self._modifier_toggle = ""   # 例: "alt"
self._trigger_toggle  = ""   # 例: "z"
self._capturing       = False
```

### reload_hotkeys()

```python
def reload_hotkeys(self):
    keyboard.unhook_all()
    hold_str   = ConfigManager.get_hotkey()
    toggle_str = ConfigManager.get_hotkey_toggle()

    mod_h, trg_h = ConfigManager.parse_hotkey(hold_str)
    mod_t, trg_t = ConfigManager.parse_hotkey(toggle_str)

    # 旧フォーマットフォールバック
    if not trg_h:
        mod_h, trg_h = "alt", "x"
    if not trg_t:
        mod_t, trg_t = "alt", "z"

    self._modifier_hold   = mod_h
    self._trigger_hold    = trg_h
    self._modifier_toggle = mod_t
    self._trigger_toggle  = trg_t

    keyboard.hook(self._on_key_event)
```

### _on_key_event()

```python
def _on_key_event(self, event):
    if self._capturing:
        return  # キャプチャ中は録音ロジック全スキップ

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

**ダブルタップロジック（`_last_press_time`、`_handle_double_tap`）は完全削除。**

### _handle_toggle()

```python
def _handle_toggle(self):
    if self.is_recording:
        self._is_toggled = False
        self.stop_and_transcribe()
    elif not self.processing:
        self._is_toggled = True
        self.start_recording()
```

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `src/config.py` | `parse_hotkey()` 追加、`get_hotkey_toggle()` / `set_hotkey_toggle()` 追加、デフォルト値更新 |
| `src/ui.py` | Hotkey セクション差し替え（Hold/Toggle 2行）、キャプチャロジック追加、`_apply_hotkey()` 更新 |
| `src/main.py` | `reload_hotkeys()` 更新、`_on_key_event()` 更新、`_handle_toggle()` 追加、ダブルタップ削除 |
| `tests/test_config.py` | `parse_hotkey()` のテスト追加、`get/set_hotkey_toggle()` のテスト追加 |

---

## スコープ外

- Shift / Win キーの修飾キーサポート（現状 Ctrl / Alt のみ）
- トリガーキーの手入力
- ホットキーの衝突検出
