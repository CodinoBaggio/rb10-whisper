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
                    model=ConfigManager.get_whisper_model(),
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
