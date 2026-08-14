import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dictionary import Dictionary


# --- build_prompt_suffix ---

def test_build_prompt_suffix_returns_empty_for_empty_list():
    assert Dictionary.build_prompt_suffix([]) == ""


def test_build_prompt_suffix_joins_terms_with_ideographic_comma():
    entries = [
        {"term": "Anthropic", "wrong": ""},
        {"term": "東商会", "wrong": ""},
        {"term": "コムテック", "wrong": ""},
    ]
    assert Dictionary.build_prompt_suffix(entries) == "Anthropic、東商会、コムテック"


def test_build_prompt_suffix_deduplicates_terms_keeping_order():
    entries = [
        {"term": "Anthropic", "wrong": "あんそろぴっく"},
        {"term": "東商会", "wrong": ""},
        {"term": "Anthropic", "wrong": "アンソロピック"},
    ]
    assert Dictionary.build_prompt_suffix(entries) == "Anthropic、東商会"


def test_build_prompt_suffix_ignores_blank_terms():
    entries = [
        {"term": "Anthropic", "wrong": ""},
        {"term": "", "wrong": "あんそろぴっく"},
        {"term": "   ", "wrong": ""},
        {"term": "東商会", "wrong": ""},
    ]
    assert Dictionary.build_prompt_suffix(entries) == "Anthropic、東商会"


def test_build_prompt_suffix_truncates_at_max_prompt_chars():
    entries = [{"term": "あ" * 30 + str(i), "wrong": ""} for i in range(10)]
    result = Dictionary.build_prompt_suffix(entries)
    assert len(result) <= Dictionary.MAX_PROMPT_CHARS


def test_build_prompt_suffix_truncation_keeps_terms_intact():
    """打ち切り時に語の途中で切らず、完全な語だけを残すこと。"""
    entries = [{"term": "あ" * 30 + str(i), "wrong": ""} for i in range(10)]
    original_terms = [e["term"] for e in entries]

    result = Dictionary.build_prompt_suffix(entries)
    kept = result.split("、")

    # 語片が混じっていない
    for term in kept:
        assert term in original_terms
    # 登録順が保たれている
    assert kept == original_terms[:len(kept)]
    # あと1語入れると上限を超える（＝詰められるだけ詰めている）
    next_index = len(kept)
    assert next_index < len(original_terms)
    over = "、".join(original_terms[:next_index + 1])
    assert len(over) > Dictionary.MAX_PROMPT_CHARS


# --- apply_replacements ---

def test_apply_replacements_skips_entries_with_blank_wrong():
    entries = [{"term": "東商会", "wrong": ""}]
    assert Dictionary.apply_replacements("東証会に行く", entries) == "東証会に行く"


def test_apply_replacements_replaces_wrong_with_term():
    entries = [{"term": "Anthropic", "wrong": "あんそろぴっく"}]
    assert Dictionary.apply_replacements(
        "あんそろぴっくのAPIを使う", entries
    ) == "AnthropicのAPIを使う"


def test_apply_replacements_handles_multiple_wrongs_for_same_term():
    entries = [
        {"term": "Anthropic", "wrong": "あんそろぴっく"},
        {"term": "Anthropic", "wrong": "アンソロピック"},
    ]
    assert Dictionary.apply_replacements(
        "あんそろぴっくとアンソロピックは同じ", entries
    ) == "AnthropicとAnthropicは同じ"


def test_apply_replacements_leaves_text_unchanged_when_no_match():
    entries = [{"term": "Anthropic", "wrong": "あんそろぴっく"}]
    assert Dictionary.apply_replacements("今日はいい天気です", entries) == "今日はいい天気です"


def test_apply_replacements_replaces_all_occurrences():
    entries = [{"term": "東商会", "wrong": "東証会"}]
    assert Dictionary.apply_replacements(
        "東証会と東証会の東証会", entries
    ) == "東商会と東商会の東商会"


# --- A: 打ち切りの greedy packing（break -> continue） ---

def test_build_prompt_suffix_packs_short_term_after_long_one_is_skipped():
    """長い語1つが上限を超えても、後続の短い語は捨てられずに詰められること。"""
    entries = [
        {"term": "ア" * 250, "wrong": ""},
        {"term": "東商会", "wrong": ""},
    ]
    result = Dictionary.build_prompt_suffix(entries)
    assert result == "東商会"


# --- B/C/D: prompt_overflow_info ---

def test_prompt_overflow_info_no_overflow():
    entries = [
        {"term": "Anthropic", "wrong": ""},
        {"term": "東商会", "wrong": ""},
    ]
    info = Dictionary.prompt_overflow_info(entries)
    assert info["truncated"] is False
    assert info["raw_length"] == len("Anthropic、東商会")
    assert info["kept_count"] == info["total_count"]


def test_prompt_overflow_info_overflow():
    entries = [{"term": "あ" * 30 + str(i), "wrong": ""} for i in range(10)]
    raw_suffix = "、".join(dict.fromkeys(e["term"] for e in entries))
    info = Dictionary.prompt_overflow_info(entries)
    assert info["truncated"] is True
    assert info["raw_length"] == len(raw_suffix)
    assert info["kept_count"] < info["total_count"]


def test_prompt_overflow_info_does_not_print(capsys):
    entries = [{"term": "あ" * 30 + str(i), "wrong": ""} for i in range(10)]
    Dictionary.prompt_overflow_info(entries)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_build_prompt_suffix_prints_warning_on_overflow(capsys):
    entries = [{"term": "あ" * 30 + str(i), "wrong": ""} for i in range(10)]
    Dictionary.build_prompt_suffix(entries)
    captured = capsys.readouterr()
    assert "Dictionary Warning" in captured.out


# --- F/G: 置換のカスケード・シャドーイング事故防止 ---

def test_apply_replacements_avoids_cascade_shadowing():
    entries = [
        {"term": "東商会", "wrong": "東証会"},
        {"term": "HSE", "wrong": "東商会"},
    ]
    assert Dictionary.apply_replacements("東証会に行く", entries) == "東商会に行く"


def test_apply_replacements_avoids_shadowing_by_shorter_wrong():
    entries = [
        {"term": "X", "wrong": "東商"},
        {"term": "東商会", "wrong": "東商回"},
    ]
    assert Dictionary.apply_replacements("東商回に行く", entries) == "東商会に行く"


# --- H: 不正なentry要素で例外を投げない ---

def test_build_prompt_suffix_ignores_invalid_entries():
    entries = [None, "文字列", {"term": 123, "wrong": None}, {"no_term_key": "x"}]
    # クラッシュしないこと。123 は str化されて有効な term として扱われる想定。
    result = Dictionary.build_prompt_suffix(entries)
    assert isinstance(result, str)


def test_apply_replacements_ignores_invalid_entries():
    entries = [None, "文字列", {"term": 123, "wrong": None}, {"no_term_key": "x"}]
    result = Dictionary.apply_replacements("テスト文", entries)
    assert isinstance(result, str)


# --- I: FILLER_PATTERNS の正本 ---

def test_filler_patterns_content():
    assert Dictionary.FILLER_PATTERNS == ["えー", "あー", "うーん", "えっと"]


# --- 漢字境界ヒューリスティック（同音異義語による複合語破損の防止） ---

def test_apply_replacements_skips_when_followed_by_kanji():
    """「蒸気」→「上記」の登録が「蒸気機関車」を「上記機関車」に壊さないこと。"""
    entries = [{"term": "上記", "wrong": "蒸気"}]
    assert Dictionary.apply_replacements("蒸気機関車の写真です", entries) == "蒸気機関車の写真です"


def test_apply_replacements_replaces_when_followed_by_hiragana():
    """単独の「蒸気」（誤認識）はひらがなが続くので正しく置換されること。"""
    entries = [{"term": "上記", "wrong": "蒸気"}]
    assert Dictionary.apply_replacements("蒸気を確認してください", entries) == "上記を確認してください"


def test_apply_replacements_replaces_at_end_of_string():
    entries = [{"term": "上記", "wrong": "蒸気"}]
    assert Dictionary.apply_replacements("それは蒸気", entries) == "それは上記"


def test_apply_replacements_skips_when_preceded_by_kanji():
    """「動車」の登録が「自動車」を壊さないこと（左側の漢字境界チェック）。"""
    entries = [{"term": "XX", "wrong": "動車"}]
    assert Dictionary.apply_replacements("自動車を運転する", entries) == "自動車を運転する"


def test_apply_replacements_katakana_wrong_ignores_kanji_boundary():
    """wrong がカタカナ等で終わる場合は、直後が漢字でもヒューリスティックの対象外で置換される。"""
    entries = [{"term": "Anthropic", "wrong": "あんそろぴっく"}]
    assert Dictionary.apply_replacements("あんそろぴっく社に問い合わせる", entries) == "Anthropic社に問い合わせる"
