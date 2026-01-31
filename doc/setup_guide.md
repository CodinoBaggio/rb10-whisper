# rb10-whisper 環境準備ガイド

このドキュメントでは、`rb10-whisper` を動作させるための環境構築手順を説明します。

## 前提条件

- **OS**: Windows 10/11
- **Python**: 3.10 以上 (3.11 推奨)
- **OpenAI API キー**: クレジットがチャージされているもの

## セットアップ手順

### 1. Python のインストール
Python がインストールされていない場合は、[python.org](https://www.python.org/) からダウンロードしてインストールしてください。インストール時、「Add Python to PATH」に必ずチェックを入れてください。

### 2. 仮想環境の作成と有効化
プロジェクトのルートディレクトリで以下のコマンドを実行します。

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. 依存ライブラリのインストール
以下のコマンドを実行してライブラリをインストールします。`requirements.txt` に含まれていない `keyring` も追加でインストールします。

```powershell
pip install -r requirements.txt
pip install keyring
```

> [!NOTE]
> `pyaudio` のインストールでエラーが出る場合は、[Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) が必要になることがあります。

### 4. アプリの起動
以下のコマンドでアプリを起動します。

```powershell
python launcher.py
```

初回起動時に API キーの入力画面が表示されます。

## EXE化する場合の手順

ビルド（EXE化）を行いたい場合は、以下の手順を実行してください。

1. 仮想環境が有効な状態で、`pyinstaller` がインストールされていることを確認します。
2. `build.bat` を実行します。

```powershell
.\build.bat
```

3. `dist/rb10-whisper.exe` が生成されます。
