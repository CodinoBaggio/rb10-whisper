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
                # promptを簡略化してAIによる過剰な推測（幻覚）を抑制
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja",
                    prompt="こんにちは。" # 最小限のプロンプトで日本語であることを示す
                )
            
            text = transcript.text
            return self._post_process(text)
            
        except Exception as e:
            print(f"Transcription Error: {e}")
            return ""

    def _post_process(self, text: str) -> str:
        """
        文字起こし結果のクリーニングと加工。幻覚の除去。
        """
        # 0. 記号のみ、または極端に短い場合は空として扱う（点や丸だけの入力を防ぐ）
        clean_text = re.sub(r'[。\.\,、 \? ！ ！ \n\t]', '', text)
        if len(clean_text) <= 1:
            return ""

        # 1. 幻覚（Hallucination）フィルター
        # 行単位や全文で完全一致、あるいは含まれている場合に除去するフレーズ
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
        
        # 全体としてこれらのフレーズしか含まれていない場合は空にする
        for phrase in hallucination_phrases:
            if re.search(f"^{phrase}[。．？！]?$", text) or text == phrase:
                return ""
            # 部分一致での除去
            text = re.sub(phrase, "", text)

        # 2. 残存フィラー除去 (念のため)
        fillers = [r"えー", r"あー", r"うーん", r"えっと"]
        for filler in fillers:
            text = re.sub(filler, "", text)

        # 3. 整形
        text = text.strip()
        
        # 最終チェック：加工後に記号だけになったり短くなりすぎたら空にする
        final_clean = re.sub(r'[。\.\,、 \? ！ ！]', '', text)
        if len(final_clean) == 0:
            return ""
            
        return text
