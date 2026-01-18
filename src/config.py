import os
import keyring
from pathlib import Path

class ConfigManager:
    """設定（APIキー）を管理するクラス (keyring使用版)"""
    
    SERVICE_NAME = "rb10-whisper"
    USER_NAME = "user_api_key" # 単一ユーザー想定なので固定

    @classmethod
    def load_api_key(cls) -> str:
        """
        OSのCredential ManagerからOpenAI APIキーを取得する。
        """
        try:
            key = keyring.get_password(cls.SERVICE_NAME, cls.USER_NAME)
            return key if key else ""
        except Exception as e:
            print(f"Keyring Load Error: {e}")
            return ""

    @classmethod
    def save_api_key(cls, api_key: str) -> None:
        """
        APIキーをOSのCredential Managerに保存する。
        """
        try:
            keyring.set_password(cls.SERVICE_NAME, cls.USER_NAME, api_key)
        except Exception as e:
            print(f"Keyring Save Error: {e}")
            # エラー時はログに出すか、UIで通知する仕組みが必要だが、
            # 現状はprintのみにとどめる

    @classmethod
    def has_valid_key(cls) -> bool:
        """
        有効そうなAPIキーが存在するか簡易チェック。
        """
        key = cls.load_api_key()
        return key.startswith("sk-") and len(key) > 20
