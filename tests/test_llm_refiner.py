import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from unittest.mock import patch, MagicMock
import pytest
from src.config import ConfigManager
from src.llm_refiner import LLMRefiner


def _make_mock_response(json_data, status=200):
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = json.dumps(json_data).encode("utf-8")
    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = mock_resp
    return mock_ctx


def test_refine_returns_original_text_when_mode_is_off():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'get_ai_mode', return_value="off"):
        refiner = LLMRefiner()
        result = refiner.refine("こんにちは えーテストです")
        assert result == "こんにちは えーテストです"


def test_refine_calls_ollama_for_refine_mode():
    ConfigManager._config_cache = None
    mock_ctx = _make_mock_response({"message": {"content": "こんにちはテストです。"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:
        
        refiner = LLMRefiner()
        result = refiner.refine("こんにちは えー テストです")
        assert result == "こんにちはテストです。"
        assert mock_urlopen.called


def test_refine_sends_casual_request_preservation_rules():
    ConfigManager._config_cache = None
    mock_ctx = _make_mock_response({"message": {"content": "このデータ保存しといて"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:

        result = LLMRefiner().refine("このデータ保存しといて")

    request = mock_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    system_prompt = payload["messages"][0]["content"]

    assert result == "このデータ保存しといて"
    assert payload["messages"][1] == {"role": "user", "content": "このデータ保存しといて"}
    assert "このデータ保存しといて" in system_prompt
    assert "このデータを保存しておきます" in system_prompt
    assert "敬語や丁寧な断定に変換しない" in system_prompt

def test_legacy_business_mode_uses_selected_text_for_editing():
    mock_ctx = _make_mock_response({"message": {"content": "お世話になっております。テストの件、承知いたしました。"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="business"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine("丁寧にして", selected_text="テストの件了解")

    assert result == "お世話になっております。テストの件、承知いたしました。"


def test_refine_fallback_to_original_text_on_error():
    ConfigManager._config_cache = None
    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch('urllib.request.urlopen', side_effect=Exception("Connection refused")):
        
        refiner = LLMRefiner()
        result = refiner.refine("テストテキスト")
        assert result == "テストテキスト"




def test_refine_falls_back_to_transcript_when_llm_output_is_unrelated():
    original = "明日の予定を確認してくれ"
    mock_ctx = _make_mock_response({"message": {"content": "月曜に電話する"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == original


def test_refine_falls_back_when_question_is_changed_into_an_answer():
    original = "明日の会議は何時からですか"
    mock_ctx = _make_mock_response({"message": {"content": "明日の会議は10時からです"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == original


def test_refine_falls_back_when_request_is_changed_into_execution_declaration():
    original = "このデータ保存しといて"
    mock_ctx = _make_mock_response({"message": {"content": "このデータを保存しておきます"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == original


@pytest.mark.parametrize("candidate", ["明日会議あるよ", "明日会議ある。"])
def test_refine_falls_back_when_spoken_question_mark_is_changed_into_statement(candidate):
    original = "明日会議ある？"
    mock_ctx = _make_mock_response({"message": {"content": candidate}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == original


@pytest.mark.parametrize(
    ("original", "candidate"),
    [
        ("明日の会議資料を確認しておいて", "明日の会議資料を確認しておきます"),
        ("明日の会議資料を確認お願いします", "明日の会議資料を確認します"),
    ],
)
def test_refine_falls_back_when_request_form_is_changed_into_execution_declaration(original, candidate):
    mock_ctx = _make_mock_response({"message": {"content": candidate}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == original


def test_refine_falls_back_when_candidate_appends_execution_and_closing_to_long_transcript():
    original = "明日の会議資料は共有フォルダへ保存したあとに関係者へ連絡する必要があります"
    candidate = f"{original}。対応します。以上です。"
    mock_ctx = _make_mock_response({"message": {"content": candidate}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == original


@pytest.mark.parametrize(
    ("original", "candidate"),
    [("俺わ行く", "俺は行く"), ("昨日わ", "昨日は")],
)
def test_refine_allows_single_particle_correction_in_short_transcript(original, candidate):
    mock_ctx = _make_mock_response({"message": {"content": candidate}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == candidate


@pytest.mark.parametrize(
    ("original", "candidate", "expected"),
    [
        ("あーちゃんに連絡して", "ちゃんに連絡して", "あーちゃんに連絡して"),
        ("えーと明日の会議を確認して", "明日の会議を確認して", "明日の会議を確認して"),
    ],
)
def test_refine_removes_only_leading_standalone_fillers(original, candidate, expected):
    mock_ctx = _make_mock_response({"message": {"content": candidate}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="refine"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx):
        result = LLMRefiner().refine(original)

    assert result == expected


@pytest.mark.parametrize(
    ("original", "candidate"),
    [
        ("確認して", "確認して。"),
        ("明日の会議は何時からですか", "明日の会議は何時からですか。"),
    ],
)
def test_limited_correction_allows_terminal_period_without_changing_sentence_form(original, candidate):
    assert LLMRefiner._is_limited_correction(original, candidate)


def test_limited_correction_rejects_internal_content_insertion():
    original = "明日の会議資料は共有フォルダへ保存したあとに関係者へ連絡する必要があります"
    candidate = original.replace("共有", "必ず共有")

    assert not LLMRefiner._is_limited_correction(original, candidate)


def test_limited_correction_rejects_terminal_content_deletion():
    original = "明日の会議資料は共有フォルダへ保存したあとに関係者へ連絡する必要があります"
    candidate = original.removesuffix("ます")

    assert not LLMRefiner._is_limited_correction(original, candidate)


def test_limited_correction_does_not_remove_space_delimited_name_as_filler():
    original = "今日は あーちゃんに連絡して"
    candidate = "今日は ちゃんに連絡して"

    assert not LLMRefiner._is_limited_correction(original, candidate)


def test_limited_correction_rejects_question_answer_after_terminal_period():
    assert not LLMRefiner._is_limited_correction(
        "この内容で問題ないですか。", "この内容で問題ないです。"
    )


def test_limited_correction_rejects_request_execution_after_terminal_period():
    assert not LLMRefiner._is_limited_correction(
        "会議資料を確認して。", "会議資料を確認します。"
    )


def test_limited_correction_rejects_internal_content_word_replacement():
    original = "明日の会議資料は共有フォルダへ保存したあとに関係者へ連絡する必要があります"
    assert not LLMRefiner._is_limited_correction(original, original.replace("明日", "今日"))


@pytest.mark.parametrize(("original", "candidate"), [("わに", "はに"), ("おに", "をに")])
def test_limited_correction_rejects_particle_replacement_at_word_start(original, candidate):
    assert not LLMRefiner._is_limited_correction(original, candidate)


def test_limited_correction_rejects_candidate_side_filler_addition():
    assert not LLMRefiner._is_limited_correction("明日の会議を確認して", "えーと明日の会議を確認して")


def test_limited_correction_rejects_content_word_replacement_for_dictionary_handling():
    # 内容語の置換はローカル判定で安全に識別できないため、既知語は辞書機能で補正する。
    assert not LLMRefiner._is_limited_correction("会義です", "会議です")


def test_limited_correction_rejects_particle_insertion_without_tokenizer():
    assert not LLMRefiner._is_limited_correction("俺行く", "俺は行く")


def test_limited_correction_rejects_question_loss_in_compound_transcript():
    assert not LLMRefiner._is_limited_correction(
        "明日会議ある？念のため確認して", "明日会議ある。念のため確認して"
    )


def test_protected_sentence_forms_include_question_position():
    assert LLMRefiner._protected_sentence_forms("明日会議ある？資料は共有済み") != LLMRefiner._protected_sentence_forms(
        "明日会議ある。資料は共有済み？"
    )


def test_limited_correction_rejects_declaration_changed_to_question():
    assert not LLMRefiner._is_limited_correction("対応します！", "対応します？")


def test_limited_correction_rejects_question_loss_before_trailing_filler():
    assert not LLMRefiner._is_limited_correction("明日会議ある？ えーと", "明日会議ある。")


def test_limited_correction_rejects_excessive_exclamation_marks():
    assert not LLMRefiner._is_limited_correction("やめて。", "やめて！！！")


@pytest.mark.parametrize(
    ("original", "candidate"),
    [
        ("株式会社", "株式は会社"),
        ("かわ", "かは"),
        ("完了", "完了は"),
        ("これわいい", "これはいい"),
    ],
)
def test_limited_correction_rejects_particle_edits_without_clear_boundaries(original, candidate):
    assert not LLMRefiner._is_limited_correction(original, candidate)


def test_business_mode_without_selection_does_not_call_ollama():
    with patch.object(ConfigManager, 'get_ai_mode', return_value="business"), \
         patch('urllib.request.urlopen') as mock_urlopen:
        result = LLMRefiner().refine("丁寧にして")

    assert result == "丁寧にして"
    mock_urlopen.assert_not_called()


def test_edit_mode_sends_spoken_instruction_and_selected_text():
    mock_ctx = _make_mock_response({"message": {"content": "選択した文を丁寧にした結果"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="edit"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:
        result = LLMRefiner().refine("丁寧にして", selected_text="これは選択中の文です")

    request = mock_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    user_content = payload["messages"][1]["content"]

    assert result == "選択した文を丁寧にした結果"
    assert "<spoken_instruction>" in user_content
    assert "丁寧にして" in user_content
    assert "<selected_text>" in user_content
    assert "これは選択中の文です" in user_content


def test_edit_mode_preserves_selected_text_whitespace_in_request():
    selected_text = "  first line\n"
    mock_ctx = _make_mock_response({"message": {"content": "edited"}})

    with patch.object(ConfigManager, 'get_ai_mode', return_value="edit"), \
         patch.object(ConfigManager, 'get_ollama_url', return_value="http://localhost:11434"), \
         patch.object(ConfigManager, 'get_ollama_model', return_value="qwen2.5:7b"), \
         patch('urllib.request.urlopen', return_value=mock_ctx) as mock_urlopen:
        LLMRefiner().refine("rewrite it", selected_text=selected_text)

    request = mock_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))

    assert "<selected_text>\n  first line\n\n</selected_text>" in payload["messages"][1]["content"]

def test_fetch_available_models():
    mock_ctx = _make_mock_response({
        "models": [
            {"name": "qwen2.5:7b"},
            {"name": "gemma3:4b"}
        ]
    })

    with patch('urllib.request.urlopen', return_value=mock_ctx):
        models = LLMRefiner.fetch_available_models("http://localhost:11434")
        assert "qwen2.5:7b" in models
        assert "gemma3:4b" in models
