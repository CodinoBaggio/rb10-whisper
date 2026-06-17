# Whisper バックエンド設定 UI — 設計仕様

**日付:** 2026-06-12  
**対象ブランチ:** feature/local-speaches-backend  
**スコープ:** `whisper_url` と `whisper_model` を Settings 画面から編集できるようにする

---

## 背景と目的

現在 `whisper_url`（speaches API のエンドポイント）と `whisper_model` は `settings.json` を直接編集しないと変更できない。Settings 画面から変更できるようにして、ファイル編集不要にする。

---

## UI レイアウト

Hotkey セクションの直下に「Backend」セクションを追加する。

```
Settings
├── [APIキー section — 既存]
├── [Recording Hotkey section — 既存]
├── [Backend section — 新規追加]  ← ここ
│   ├── Label: "Whisper URL:"
│   ├── Entry: URL入力フィールド（自由入力）
│   ├── Label: "Model:"
│   ├── Entry または Combobox: モデル（URL に応じて動的切り替え）
│   ├── Button: "Apply Backend"
│   └── Label: "設定を変更したら「Apply Backend」を押してください"
└── [Microphone section — 既存]
```

---

## モデルフィールドの動的切り替え

URL の内容に応じてモデル入力ウィジェットを切り替える。

| URL の内容 | モデルフィールド | 動作 |
|---|---|---|
| `localhost` または `127.0.0.1` を含む | `ttk.Combobox`（readonly） | `/v1/models` から取得した一覧を選択肢に設定 |
| 上記以外（外部 URL） | `tk.Entry`（自由入力） | 取得しない、手入力のみ |

### フェッチのタイミング

1. **Settings 画面を開いた時**: 保存済み URL が localhost → 即座にバックグラウンドフェッチ開始
2. **URL 欄のフォーカスが外れた時** (`<FocusOut>`): 新しい URL が localhost → フェッチして Combobox に切り替え、外部 URL → Entry に切り替え

### フェッチ中の状態

- モデルフィールドを `state="disabled"` に設定
- 表示テキストを `"Fetching..."` に変更
- フェッチ完了後に enable + Combobox に切り替え

### Combobox の初期選択

config に保存されたモデル名が取得した一覧に含まれている → そのモデルを選択  
含まれていない → 先頭のモデルを選択

### フェッチ失敗時

- speaches が未起動 / タイムアウト / ネットワークエラーなど
- エラーダイアログは出さない
- Entry にフォールバックし、config に保存されている現在のモデル名を表示

---

## Apply ボタンの動作

`Apply Backend` ボタンを押したとき:

1. URL のバリデーション（空または `http` で始まらない場合は `messagebox.showerror` を表示して中断）
2. バックグラウンドスレッドで `ConfigManager.set_whisper_url(url)` と `ConfigManager.set_whisper_model(model)` を呼ぶ
3. 保存完了後、`_on_save_completed("Backend [URL] applied!")` を呼ぶ（ウィンドウを閉じる）
4. 例外発生時は `messagebox.showerror` を表示

---

## ConfigManager の変更

`src/config.py` に以下2メソッドを追加する（`set_hotkey` と同パターン）。

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

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `src/config.py` | `set_whisper_url()` / `set_whisper_model()` を追加 |
| `src/ui.py` | Backend セクション追加、動的ウィジェット切り替え、Apply ロジック |
| `tests/test_config.py` | `test_set_whisper_url_saves_value()` / `test_set_whisper_model_saves_value()` を追加 |

---

## テスト方針

### 自動テスト（`tests/test_config.py`）

- `test_set_whisper_url_saves_value()`: 保存後 `get_whisper_url()` で値が返ること
- `test_set_whisper_model_saves_value()`: 保存後 `get_whisper_model()` で値が返ること

### 手動確認

- Settings を開いたとき、保存済みの URL が localhost なら Combobox が表示されること
- URL を外部に変えて blur → Entry に切り替わること
- URL を localhost に戻して blur → Combobox に切り替わり、モデル一覧が取得されること
- speaches を止めた状態でフェッチ失敗 → Entry にフォールバックすること
- Apply → `settings.json` に URL とモデルが保存されていること

---

## スコープ外（YAGNI）

- モデル一覧の手動リフレッシュボタン（将来追加可能）
- URL の疎通チェック（Test Connection ボタン）
- `whisper_model` に対する外部 URL 時のプリセット一覧
