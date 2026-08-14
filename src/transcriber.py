import os
from openai import OpenAI
from src.config import ConfigManager
from src.llm_refiner import LLMRefiner
from src.dictionary import Dictionary
import re

class Transcriber:
    def _make_client(self) -> tuple:
        """現在の config に基づいて (OpenAI client, model) を返す"""
        if ConfigManager.get_backend_type() == "openai":
            api_key = ConfigManager.load_api_key() or "dummy"
            base_url = ConfigManager.get_openai_url() or None
            return OpenAI(api_key=api_key, base_url=base_url, timeout=30.0), "whisper-1"
        else:
            return (
                OpenAI(api_key="dummy", base_url=ConfigManager.get_whisper_url(), timeout=30.0),
                ConfigManager.get_whisper_model(),
            )

    def check_connection(self) -> bool:
        """バックエンドへの接続確認。OpenAI モードは常に True を返す。"""
        if ConfigManager.get_backend_type() == "openai":
            return True
        try:
            client, _ = self._make_client()
            client.models.list()
            return True
        except Exception:
            return False

    def transcribe(self, audio_file_path: str, selected_text: str | None = None) -> str:
        """音声ファイルをテキストに変換する"""
        try:
            client, model = self._make_client()
            entries = ConfigManager.get_dictionary()

            # 登録語を prompt の末尾へ（Whisper は末尾ほど影響が強い）
            prompt = "こんにちは。" + Dictionary.build_prompt_suffix(entries)

            with open(audio_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language="ja",
                    prompt=prompt
                )
            text = transcript.text
            clean_text = self._post_process(text)
            if not clean_text:
                return ""

            clean_text = Dictionary.apply_replacements(clean_text, entries)
            return LLMRefiner().refine(clean_text, selected_text)
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

        fillers = Dictionary.FILLER_PATTERNS
        for filler in fillers:
            text = re.sub(filler, "", text)

        text = text.strip()

        final_clean = re.sub(r'[。\.\,、 \? ！ ！]', '', text)
        if len(final_clean) == 0:
            return ""

        return text
