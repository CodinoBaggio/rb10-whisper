# Safe Dictation and Explicit AI Edit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent ordinary dictation from accepting unrelated LLM output while allowing intentional rewrites only through an explicit selected-text mode.

**Architecture:** `LLMRefiner` owns mode-specific prompts and the local limited-output guard. `AudioInputApp` captures a selection only for edit mode and passes it through `Transcriber`, keeping the existing single transcription and paste pipeline.

**Tech Stack:** Python 3.11, Tkinter, pyperclip, pyautogui, Ollama HTTP API, pytest.

## Global Constraints

- Normal `refine` sends one Ollama request; never add a second model request for validation.
- Free-form rewrite requires explicit `edit` mode and a non-empty active selection.
- Do not persist transcript, selection, prompt, or output history.
- Preserve the existing uncommitted casual-style prompt changes.

---

### Task 1: Constrain and guard ordinary AI refinement

**Files:**
- Modify: `src/llm_refiner.py`
- Test: `tests/test_llm_refiner.py`

**Interfaces:**
- Produces: `LLMRefiner.refine(text: str, selected_text: str | None = None) -> str`
- Produces: local limited-output validation used only by `refine` mode.

- [x] **Step 1: Write failing tests**

```python
def test_refine_returns_original_text_when_llm_output_diverges():
    assert LLMRefiner().refine("明日の予定を確認してくれ") == "明日の予定を確認してくれ"

def test_edit_without_selection_does_not_call_ollama():
    assert LLMRefiner().refine("丁寧にして") == "丁寧にして"
```

- [x] **Step 2: Run targeted tests and confirm RED**

Run: `pytest tests/test_llm_refiner.py -q`

- [x] **Step 3: Add the minimal mode dispatch and guard**

```python
if ai_mode == "refine":
    return self._fallback_if_divergent(text, self._chat(...))
if ai_mode in {"edit", "business"} and selected_text:
    return self._chat(...)
return text
```

- [x] **Step 4: Run targeted tests and confirm GREEN**

Run: `pytest tests/test_llm_refiner.py -q`

### Task 2: Pass captured selection through the transcription pipeline

**Files:**
- Modify: `src/transcriber.py`
- Modify: `src/main.py`
- Test: `tests/test_transcriber.py`

**Interfaces:**
- Consumes: `LLMRefiner.refine(text, selected_text)` from Task 1.
- Produces: `Transcriber.transcribe(audio_file_path, selected_text=None) -> str`.

- [x] **Step 1: Write a failing transcriber test**

```python
result = Transcriber().transcribe("dummy_file.wav", selected_text="選択中の文")
mock_refiner_inst.refine.assert_called_once_with("こんにちは テストです", "選択中の文")
```

- [x] **Step 2: Run targeted test and confirm RED**

Run: `pytest tests/test_transcriber.py -q`

- [x] **Step 3: Add selection capture and parameter forwarding**

```python
selection = self._capture_ai_edit_selection()
threading.Thread(target=self._transcribe_thread, args=(audio_path, selection)).start()
```

The capture must use a clipboard marker to distinguish no selection, restore the previous clipboard value, and return `None` on error.

- [x] **Step 4: Run targeted test and confirm GREEN**

Run: `pytest tests/test_transcriber.py -q`

### Task 3: Expose the explicit mode and verify the integration

**Files:**
- Modify: `src/config.py`
- Modify: `src/ui.py`
- Test: `tests/test_llm_refiner.py`

- [x] **Step 1: Write a failing legacy-mode / selected-edit payload test**

```python
assert payload["messages"][1]["content"] == expected_edit_payload
```

- [x] **Step 2: Run targeted test and confirm RED**

Run: `pytest tests/test_llm_refiner.py -q`

- [x] **Step 3: Implement the `edit` setting label and legacy compatibility**

The UI lists `off`, limited `refine`, and `edit (selection required)`. Existing `business` settings are accepted as selection-required edit mode.

- [x] **Step 4: Run the complete suite and inspect the diff**

Run: `pytest -q`

- [x] **Step 5: Manually verify the running app**

Select text in a Windows application, select AI Edit in Settings, dictate an edit instruction, and verify the selection is replaced. With no selection, verify the dictated text is pasted without free-form rewrite.
