import os
import keyring
import json
from pathlib import Path

class ConfigManager:
    """設定（APIキー）を管理するクラス (keyring使用版)"""
    
    SERVICE_NAME = "rb10-whisper"
    USER_NAME = "user_api_key" # 単一ユーザー想定なので固定
    _config_cache = None

    @classmethod
    def load_api_key(cls) -> str:
        """OSのCredential ManagerからOpenAI APIキーを取得する。"""
        try:
            key = keyring.get_password(cls.SERVICE_NAME, cls.USER_NAME)
            return key if key else ""
        except Exception as e:
            print(f"Keyring Load Error: {e}")
            return ""

    @classmethod
    def save_api_key(cls, api_key: str) -> None:
        """APIキーをOSのCredential Managerに保存する。"""
        try:
            keyring.set_password(cls.SERVICE_NAME, cls.USER_NAME, api_key)
        except Exception as e:
            print(f"Keyring Save Error: {e}")

    @classmethod
    def has_valid_key(cls) -> bool:
        """有効そうなAPIキーが存在するか簡易チェック。"""
        key = cls.load_api_key()
        return key.startswith("sk-") and len(key) > 20

    @classmethod
    def _get_config_path(cls) -> Path:
        """設定ファイルのパスを取得"""
        app_data = os.getenv("APPDATA")
        config_dir = Path(app_data) / "rb10-whisper"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "settings.json"

    @classmethod
    def load_config(cls) -> dict:
        """一般設定をロード（キャッシュ優先）"""
        if cls._config_cache is not None:
            return cls._config_cache

        path = cls._get_config_path()
        defaults = {
            "hotkey": "alt+x",
            "hotkey_toggle": "alt+z",
            "backend_type": "local",
            "whisper_url": "http://localhost:8001/v1",
            "whisper_model": "Systran/faster-whisper-large-v3",
            "openai_url": "https://api.openai.com/v1",
            "docker_container": "",
            "mic_device": None,
            "ai_mode": "off",
            "ollama_url": "http://localhost:11434",
            "ollama_model": "qwen2.5:7b",
            "dictionary": []
        }
        if not path.exists():
            cls._config_cache = defaults
            return defaults
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # デフォルト値をマージ
                for k, v in defaults.items():
                    if k not in config:
                        config[k] = v
                cls._config_cache = config
                return config
        except Exception as e:
            print(f"Config Load Error: {e}")
            cls._config_cache = defaults
            return defaults

    @classmethod
    def save_config(cls, config: dict) -> None:
        """一般設定をセーブ（キャッシュも更新）"""
        cls._config_cache = config
        path = cls._get_config_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Config Save Error: {e}")

    @classmethod
    def parse_hotkey(cls, hotkey_str: str) -> tuple[str, str]:
        """`"ctrl+x"` → `("ctrl", "x")`. `+` がない旧フォーマットは `("", "")` を返す"""
        if "+" not in hotkey_str:
            return ("", "")
        parts = hotkey_str.split("+", 1)
        return (parts[0].lower(), parts[1].lower())

    @classmethod
    def get_hotkey(cls) -> str:
        """設定からホットキーを取得"""
        config = cls.load_config()
        return config.get("hotkey", "shift")

    @classmethod
    def set_hotkey(cls, hotkey: str) -> None:
        """ホットキーを設定に保存"""
        config = cls.load_config()
        config["hotkey"] = hotkey
        cls.save_config(config)

    @classmethod
    def get_backend_type(cls) -> str:
        """バックエンド種別を取得: 'local' または 'openai'"""
        config = cls.load_config()
        return config.get("backend_type", "local")

    @classmethod
    def set_backend_type(cls, backend_type: str) -> None:
        config = cls.load_config()
        config["backend_type"] = backend_type
        cls.save_config(config)

    @classmethod
    def get_openai_url(cls) -> str:
        """OpenAI API の URL を取得"""
        config = cls.load_config()
        return config.get("openai_url", "https://api.openai.com/v1")

    @classmethod
    def set_openai_url(cls, url: str) -> None:
        config = cls.load_config()
        config["openai_url"] = url
        cls.save_config(config)

    @classmethod
    def get_whisper_url(cls) -> str:
        """文字起こしバックエンドの URL を取得"""
        config = cls.load_config()
        return config.get("whisper_url", "http://localhost:8001/v1")

    @classmethod
    def get_whisper_model(cls) -> str:
        """使用する Whisper モデル名を取得"""
        config = cls.load_config()
        return config.get("whisper_model", "Systran/faster-whisper-large-v3")

    @classmethod
    def set_whisper_url(cls, url: str) -> None:
        """文字起こしバックエンドの URL を設定に保存"""
        config = cls.load_config()
        config["whisper_url"] = url
        cls.save_config(config)

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

    @classmethod
    def set_whisper_model(cls, model: str) -> None:
        """使用する Whisper モデル名を設定に保存"""
        config = cls.load_config()
        config["whisper_model"] = model
        cls.save_config(config)

    @classmethod
    def get_docker_container(cls) -> str:
        """Docker コンテナ名を取得（自動起動用）"""
        config = cls.load_config()
        return config.get("docker_container", "")

    @classmethod
    def set_docker_container(cls, name: str) -> None:
        """Docker コンテナ名を設定に保存"""
        config = cls.load_config()
        config["docker_container"] = name
        cls.save_config(config)

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

    @classmethod
    def get_ai_mode(cls) -> str:
        """Return the configured AI mode."""
        config = cls.load_config()
        return config.get("ai_mode", "off")

    @classmethod
    def set_ai_mode(cls, mode: str) -> None:
        """AI整形モードを設定に保存"""
        config = cls.load_config()
        config["ai_mode"] = mode
        cls.save_config(config)

    @classmethod
    def get_ollama_url(cls) -> str:
        """Ollama API の URL を取得"""
        config = cls.load_config()
        return config.get("ollama_url", "http://localhost:11434")

    @classmethod
    def set_ollama_url(cls, url: str) -> None:
        """Ollama API の URL を設定に保存"""
        config = cls.load_config()
        config["ollama_url"] = url
        cls.save_config(config)

    @classmethod
    def get_ollama_model(cls) -> str:
        """使用する Ollama モデル名を取得"""
        config = cls.load_config()
        return config.get("ollama_model", "qwen2.5:7b")

    @classmethod
    def set_ollama_model(cls, model: str) -> None:
        """使用する Ollama モデル名を設定に保存"""
        config = cls.load_config()
        config["ollama_model"] = model
        cls.save_config(config)

    @classmethod
    def get_dictionary(cls) -> list[dict]:
        """音声入力辞書のエントリ一覧を取得"""
        config = cls.load_config()
        return list(config.get("dictionary", []))  # 浅いコピーを返す

    @classmethod
    def set_dictionary(cls, entries: list[dict]) -> None:
        """音声入力辞書のエントリ一覧を設定に保存"""
        config = cls.load_config()
        config["dictionary"] = entries
        cls.save_config(config)

