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
        defaults = {"hotkey": "shift"}
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
