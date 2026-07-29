# Safe Dictation and Explicit AI Edit Design

## Goal

Keep ordinary voice dictation fast and constrained while requiring an explicit mode and a real text selection for free-form AI rewriting.

## Decisions

- `refine` remains a single Ollama request, but the system prompt permits only filler removal and minimal corrections. It must preserve meaning and speaking style.
- A local output guard runs after that one request. It never calls another model. It rejects an empty output or one whose normalized length / character overlap differs materially from the dictated transcript, then returns the original transcript.
- A new `edit` mode is the only free-form rewrite path. The app captures the active selection before recording. If no selection is captured, it uses the ordinary limited-refinement path instead of calling the edit prompt.
- `business` remains recognized as a legacy setting and follows the same selection-required edit path. The settings UI exposes only `edit` for new choices.
- No transcript, selection, prompt, or output history is persisted.

## Data Flow

1. `AudioInputApp.start_recording()` captures the active selection only in `edit` mode, restoring the prior clipboard immediately.
2. `Transcriber.transcribe()` obtains Whisper text and existing deterministic cleanup.
3. `LLMRefiner.refine(clean_text, selected_text)` dispatches either limited `refine` or explicit `edit`.
4. Limited `refine` applies the local divergence guard before the existing paste operation.
5. Explicit `edit` returns the AI-edited selected text without the limited-mode divergence guard, because a substantial rewrite is the requested behavior.

## Guard Rule

After removing whitespace and punctuation, limited-mode output must keep at least 60% of the normalized characters of both the source and candidate, and its normalized length must remain between 50% and 180% of the source. Otherwise the original transcript is pasted.

## Latency and Privacy

The normal path keeps exactly one Ollama call. The guard is an in-process character count comparison and selection capture happens before recording, so no additional inference or synchronous logging is added. No history is written.

## Test Strategy

- Unit tests prove a divergent LLM response falls back to the transcript.
- Unit tests prove `edit` without a selection does not call Ollama.
- Unit tests prove `edit` with a selection uses the edit request payload.
- Transcriber integration tests prove the captured selection reaches `LLMRefiner`.
- Existing test suite is run after the changes. Manual verification covers selected-text replacement in a real Windows application.
