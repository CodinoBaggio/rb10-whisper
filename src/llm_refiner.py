import urllib.request
import json
from src.config import ConfigManager


class LLMRefiner:
    """Ollama などのローカル LLM を使用してテキストを整形・推敲するクラス"""

    PROMPTS = {
        "refine": (
            "あなたは高精度な日本語文章校正アシスタントです。\n"
            "入力された音声認識テキストから、「えー」「あー」「えっと」などの不要なフィラーを取り除き、誤字脱字や不自然な助詞のみを修正してください。\n"
            "【厳格な制約事項】\n"
            "・入力テキストに存在しない意味や言葉（「〜ありがとう」等の感謝表現や補完）を絶対に書き加えたり、文末を付け足したりしないでください。\n"
            "・話し手の元の文体・語尾（「〜してくれ」「〜だ・である」「〜です・ます」など）やニュアンスは完全にそのまま保持してください。\n"
            "・解説や前置き、挨拶は一切出力せず、修正後のテキストのみを出力してください。\n\n"
            "【出力例】\n"
            "入力: えーっと、修正しないでくれ\n"
            "出力: 修正しないでくれ\n\n"
            "入力: あー、これ明日までにやってくれ\n"
            "出力: これ明日までにやってくれ\n\n"
            "入力: えー、本日の会議の件ですが、よろしくお願いします\n"
            "出力: 本日の会議の件ですが、よろしくお願いします"
        ),
        "business": (
            "あなたはビジネスコミュニケーションの専門アシスタントです。\n"
            "入力された音声認識テキストを、ビジネスメールやチャットでそのまま使える丁寧な敬語・ビジネスマナーに適した文面に変換してください。\n"
            "注意：解説や前置き、挨拶は一切出力せず、変換後のテキストのみを出力してください。"
        )
    }

    def refine(self, text: str) -> str:
        """Config の設定に従ってテキストを LLM で整形する"""
        if not text or not text.strip():
            return text

        ai_mode = ConfigManager.get_ai_mode()
        if ai_mode == "off" or ai_mode not in self.PROMPTS:
            return text

        system_prompt = self.PROMPTS[ai_mode]
        ollama_url = ConfigManager.get_ollama_url().rstrip('/')
        ollama_model = ConfigManager.get_ollama_model()

        payload = {
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "stream": False,
            "keep_alive": "1h",
            "options": {
                "temperature": 0.0
            }
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{ollama_url}/api/chat",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    message = data.get("message", {})
                    refined_text = message.get("content", "").strip()
                    return refined_text if refined_text else text
                else:
                    print(f"Ollama API Error: status_code={response.status}")
                    return text
        except Exception as e:
            print(f"LLM Refine Exception: {e}")
            return text

    @classmethod
    def fetch_available_models(cls, ollama_url: str) -> list[str]:
        """Ollama サーバーから利用可能なモデル一覧を取得する"""
        try:
            url = ollama_url.rstrip('/') + "/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return models
            return []
        except Exception as e:
            print(f"Fetch Ollama Models Error: {e}")
            return []

