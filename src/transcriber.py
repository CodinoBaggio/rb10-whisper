import os
from openai import OpenAI, APITimeoutError
from src.config import ConfigManager
import re

class Transcriber:
    def __init__(self):
        self.api_key = ConfigManager.load_api_key()
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, timeout=30.0)

    def reload_key(self):
        """APIキーを再読み込みする"""
        self.api_key = ConfigManager.load_api_key()
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, timeout=30.0)

    def transcribe(self, audio_file_path: str) -> str:
        """
        音声ファイルをテキストに変換する
        """
        if not self.client:
            self.reload_key()
            if not self.client:
                raise ValueError("API Key is not set.")

        try:
            with open(audio_file_path, "rb") as audio_file:
                # Whisper API 呼び出し
                # promptパラメータフィラー除去を指示
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja",
                    prompt="すべてのフィラー（えー、あー、うーん）を取り除き、自然な日本語の文章に整形してください。句読点を適切に補ってください。"
                )
            
            text = transcript.text
            return self._post_process(text)
            
        except Exception as e:
            print(f"Transcription Error: {e}")
            return ""

    def _post_process(self, text: str) -> str:
        """
        文字起こし結果のクリーニングと加工
        """
        # 1. 幻覚（Hallucination）フィルター
        hallucination_phrases = [
            r"ご視聴ありがとうございました",
            r"チャンネル登録お願いします",
            r"高評価お願いします",
            r"おかげさまで", # 文脈によるが、Whisper特有の幻覚でよく出る
            r"字幕作成",
            r"視聴してくれてありがとう",
        ]
        
        for phrase in hallucination_phrases:
            # フレーズが含まれていたら、その行ごと消すか、空文字列にする
            # 完全に一致する場合や、文末に付くケースが多い。
            # ここでは単純に文字列が含まれていたら除去する
            text = re.sub(phrase, "", text)

        # 2. 残存フィラー除去 (念のため)
        fillers = [r"えー", r"あー", r"うーん", r"えっと"]
        for filler in fillers:
            text = re.sub(filler, "", text)

        # 3. 整形
        text = text.strip()
        
        return text
