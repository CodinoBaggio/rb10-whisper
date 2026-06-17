# Design: ローカル speaches バックエンドへの切り替え

**Date:** 2026-06-09  
**Branch:** `feature/local-speaches-backend`  
**Status:** Approved

---

## 概要

OpenAI Whisper API（クラウド）への依存をなくし、ローカルで稼働する speaches Docker コンテナ（`faster-whisper-large-v3` + `int8`）を文字起こしバックエンドとして使用する。

- API コスト: ゼロ
- オフライン動作: 可能
- 精度: `whisper-1`（large-v2 ベース）より新しい large-v3 を使用

---

## バックエンド構成

| 項目 | 値 |
|---|---|
| コンテナ名 | `whisper-server` |
| イメージ | `ghcr.io/speaches-ai/speaches:latest-cuda` |
| ポート | `8000` |
| モデル | `Systran/faster-whisper-large-v3` |
| 量子化 | `int8` |
| VAD フィルター | 有効 |
| API 互換性 | OpenAI 互換（`/v1/audio/transcriptions`） |

---

## データフロー

```
F2 押す → 録音（audio.py） → WAV 一時ファイル
  → POST localhost:8000/v1/audio/transcriptions
  → テキスト返却
  → ポストプロセス（フィラー除去・幻覚フィルター）
  → クリップボード経由 Ctrl+V でペースト
  → WAV 一時ファイル削除（finally ブロック）
```

起動時フロー:
```
アプリ起動
  └─ localhost:8000/v1/models に接続チェック
      ├─ 成功 → "Ready" ログ出力、ホットキー待機
      └─ 失敗 → messagebox.showwarning() でユーザーに通知
               → アプリは起動継続（録音試行時に error.log へ記録して終了）
```

---

## 変更ファイル（3ファイルのみ）

### src/config.py

- `defaults` に `"whisper_url": "http://localhost:8000/v1"` を追加
- `get_whisper_url()` クラスメソッドを追加

### src/transcriber.py

- `__init__`: `api_key` 引数を廃止し `api_key="dummy"` 固定、`base_url=ConfigManager.get_whisper_url()` を追加
- `reload_key()`: 削除（呼び出し元がなくなるため）
- `transcribe()`: モデル名を `"whisper-1"` → `"Systran/faster-whisper-large-v3"` に変更
- `check_connection()`: 新規追加（`models.list()` で疎通確認、`bool` を返す）
- APIキー未設定ガードを削除

### src/main.py

- `_check_api_key_on_startup()` → `_check_connection_on_startup()` に置き換え
  - `ConfigManager.has_valid_key()` チェック削除
  - `transcriber.check_connection()` を呼び出し
  - 失敗時 `messagebox.showwarning()` 表示
- `toggle_recording()` の `has_valid_key()` ガード削除
- `_handle_double_tap()` の `has_valid_key()` ガード削除
- `_open_settings()` の `on_close` コールバック内 `transcriber.reload_key()` 呼び出し削除

---

## 変更しないファイル

- `src/audio.py` — 変更なし
- `src/ui.py` — 変更なし（Settings 画面の API キー欄はそのまま残す）

---

## エラーハンドリング

| シナリオ | 挙動 |
|---|---|
| 起動時に speaches が落ちている | `showwarning()` ポップアップ → アプリ継続起動 |
| 文字起こし中に接続が切れた | 既存 `except Exception` が補足 → `error.log` 記録 → オーバーレイ非表示 |
| speaches が返す空テキスト | 既存 `_post_process()` が処理 → 変更なし |

---

## 対象外スコープ

以下は本設計に含まない（将来の拡張候補）:

- Settings UI への `whisper_url` 入力欄追加
- OpenAI API へのフォールバック
- モデル切り替え UI
