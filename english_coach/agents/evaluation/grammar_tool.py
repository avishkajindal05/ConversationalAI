# ─── agents/evaluation/grammar_tool.py ───
"""Optional deterministic grammar corrections via LanguageTool (offline).

The LLM does the *scoring* (see grammar.py). This module is a best-effort
add-on that supplies a few *verified* corrections for the report when
LanguageTool is installed. It is entirely optional:

- LanguageTool needs Java plus a one-time (~200 MB) engine download, so it may
  not be present. Every entry point is fenced; on any failure the caller simply
  gets no extra corrections and falls back to the LLM's own suggestions.
- Its recall on L2 learner errors (tense, articles, prepositions) is limited and
  it emits style/dialect noise, so it is used only to *enrich* corrections,
  never to change the score.
"""

from __future__ import annotations

from english_coach.core.logger import logger

# Categories that are style/dialect/spacing noise for a spoken-English learner,
# not the grammar mistakes we care about.
_IGNORED_CATEGORIES = {
    "TYPOGRAPHY",
    "CASING",
    "WHITESPACE",
    "PUNCTUATION",
    "REDUNDANCY",
    "STYLE",
    "BRITISH_ENGLISH",
    "AMERICAN_ENGLISH",
}

_tool = None
_unavailable = False


def _get_tool():
    """Lazily create a single LanguageTool instance, or None if unavailable."""
    global _tool, _unavailable
    if _tool is not None or _unavailable:
        return _tool
    try:
        import language_tool_python

        _tool = language_tool_python.LanguageTool("en-US")
        logger.info("LanguageTool loaded for grammar corrections.")
    except Exception as exc:  # ImportError, no Java, download failure, etc.
        _unavailable = True
        logger.info("LanguageTool unavailable; using LLM-only grammar: %s", exc)
    return _tool


def _learner_text(transcript: str) -> str:
    """Keep only the learner's ("user:") turns from the transcript."""
    turns = [
        line.strip()[len("user:"):].strip()
        for line in transcript.splitlines()
        if line.strip().lower().startswith("user:")
    ]
    return " ".join(turns) if turns else transcript


def verified_corrections(transcript: str, limit: int = 6) -> list[str]:
    """Return up to `limit` "wrong -> right" corrections, or [] if unavailable."""
    tool = _get_tool()
    if tool is None:
        return []
    text = _learner_text(transcript)
    try:
        matches = tool.check(text)
    except Exception as exc:
        logger.info("LanguageTool check failed: %s", exc)
        return []

    corrections: list[str] = []
    for m in matches:
        if getattr(m, "category", "") in _IGNORED_CATEGORIES:
            continue
        if not m.replacements:
            continue
        span = text[m.offset : m.offset + m.error_length].strip()
        suggestion = m.replacements[0].strip()
        if span and suggestion and span.lower() != suggestion.lower():
            corrections.append(f"{span} -> {suggestion}")
        if len(corrections) >= limit:
            break
    return corrections
