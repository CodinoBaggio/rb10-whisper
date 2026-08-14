import re


class Dictionary:
    """辞書エントリから prompt 補助文字列を組み立て、誤認識の置換を行う。"""

    MAX_PROMPT_CHARS = 200  # Whisper prompt の上限(約224トークン)への保守的な文字数近似。
                             # 日本語は1文字が1トークン超になりうるため余裕を持たせている。
                             # ベースプロンプト "こんにちは。" 分はこの予算に含めていない(短いため実害小)。

    FILLER_PATTERNS = ["えー", "あー", "うーん", "えっと"]  # フィラー除去パターンの正本

    @classmethod
    def _unique_terms(cls, entries: list[dict]) -> list[str]:
        """entries から有効な term だけを重複除去して取り出す（副作用なし）。不正な要素は無視する。"""
        terms = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            term = str(entry.get("term") or "").strip()
            if term:
                terms.append(term)
        return list(dict.fromkeys(terms))

    @classmethod
    def _pack_within_limit(cls, unique_terms: list[str]) -> list[str]:
        """MAX_PROMPT_CHARS に収まるだけ、語単位で詰め込む（continueで次の語を試す。printしない）。"""
        kept: list[str] = []
        length = 0
        for term in unique_terms:
            needed = len(term) if not kept else len(term) + 1  # 区切りの「、」の分
            if length + needed > cls.MAX_PROMPT_CHARS:
                continue  # break ではなく continue。この語は諦めて次を試す
            kept.append(term)
            length += needed
        return kept

    @classmethod
    def build_prompt_suffix(cls, entries: list[dict]) -> str:
        """term を重複除去して「、」で連結する。実際に文字起こし時に呼ばれる想定（超過時にprint警告する）。"""
        unique_terms = cls._unique_terms(entries)
        if not unique_terms:
            return ""

        raw_suffix = "、".join(unique_terms)
        if len(raw_suffix) <= cls.MAX_PROMPT_CHARS:
            return raw_suffix

        kept = cls._pack_within_limit(unique_terms)
        print(
            f"Dictionary Warning: prompt suffix exceeds {cls.MAX_PROMPT_CHARS} chars "
            f"({len(raw_suffix)}). Kept {len(kept)}/{len(unique_terms)} terms."
        )
        return "、".join(kept)

    @classmethod
    def prompt_overflow_info(cls, entries: list[dict]) -> dict:
        """UI表示専用。printしない。切り詰め前の生の長さ・採用語数・総語数を返す。"""
        unique_terms = cls._unique_terms(entries)
        raw_length = len("、".join(unique_terms)) if unique_terms else 0
        truncated = raw_length > cls.MAX_PROMPT_CHARS
        kept_count = len(cls._pack_within_limit(unique_terms)) if truncated else len(unique_terms)
        return {
            "raw_length": raw_length,
            "truncated": truncated,
            "kept_count": kept_count,
            "total_count": len(unique_terms),
        }

    @classmethod
    def apply_replacements(cls, text: str, entries: list[dict]) -> str:
        """wrong が空でない行について、text 中の wrong を term へ置換する。
        長い wrong を優先してマッチさせ、置換結果が他ルールに再度食われない単一パス方式。
        漢字境界ヒューリスティック（_looks_like_compound_boundary）により、
        同音異義語の登録が既存の正しい複合語（例: 「蒸気」→「上記」の登録が「蒸気機関車」を壊す）
        を破損させることを防ぐ。
        """
        pairs = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            term = str(entry.get("term") or "").strip()
            wrong = str(entry.get("wrong") or "").strip()
            if term and wrong:
                pairs.append((wrong, term))

        if not pairs:
            return text

        # 長い wrong を優先（同じ開始位置で短い方に先取りされるのを防ぐ）
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        mapping = dict(pairs)
        pattern = re.compile("|".join(re.escape(wrong) for wrong, _ in pairs))

        def _replace(m: re.Match) -> str:
            wrong = m.group(0)
            if cls._looks_like_compound_boundary(text, m.start(), m.end(), wrong):
                return wrong
            return mapping[wrong]

        return pattern.sub(_replace, text)

    @classmethod
    def _looks_like_compound_boundary(cls, text: str, start: int, end: int, wrong: str) -> bool:
        """漢字境界ヒューリスティック。

        マッチした wrong の前後どちらかが漢字で連続している場合、既存の複合語の一部（例:
        「蒸気機関車」の中の「蒸気」）である可能性が高いとみなし、置換をスキップする。
        wrong 自体がひらがな・カタカナ始まり/終わりの場合は誤爆しにくいため対象外とする。
        完全な解決策ではないが、日本語の同音異義語による事故を実用上大きく減らせる。
        """
        if wrong and cls._is_kanji(wrong[-1]):
            after = text[end:end + 1]
            if cls._is_kanji(after):
                return True
        if wrong and cls._is_kanji(wrong[0]):
            before = text[start - 1:start] if start > 0 else ""
            if cls._is_kanji(before):
                return True
        return False

    @staticmethod
    def _is_kanji(ch: str) -> bool:
        """CJK統合漢字（拡張Aを含む）の範囲かどうかを判定する。"""
        if not ch:
            return False
        code = ord(ch)
        return 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF
