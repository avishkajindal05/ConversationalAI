# ─── coach/analysis.py ───
"""The single structured analysis call.

One local LLM call turns a transcript (+ any issues left open from the
candidate's last session) into a validated `Analysis`. Because a small model
is not perfectly reliable at strict JSON, the raw output is validated against
the Pydantic schema and the call is retried on failure.
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from english_coach.coach.schema import Analysis, validate_llm_payload
from english_coach.core.logger import logger
from english_coach.core.settings import settings

MAX_ATTEMPTS = 3
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

SYSTEM_PROMPT = """You are a communication coach analysing a transcript of a \
practice conversation. Judge ONLY the user's messages (the coach's turns are \
context). Score five metrics 0-100 and, if prior open issues are given, judge \
each as improved, unchanged, or worse with brief evidence from THIS transcript. \
Also flag any NEW issues.

Return STRICT JSON with exactly these keys. Every <...> is a placeholder you \
MUST replace with real content grounded in the transcript - never copy the \
placeholder text itself.
{
  "scores": {"fluency": <0-100>, "clarity": <0-100>, "vocabulary": <0-100>, "grammar": <0-100>, "confidence": <0-100>},
  "summary": "<two or three encouraging, specific sentences about how the user communicated>",
  "strengths": ["<a specific thing the user did well>"],
  "prior_issue_verdicts": [
    {"description": "<the prior issue, copied verbatim>", "status": "improved|unchanged|worse", "evidence": "<short reason from this transcript>"}
  ],
  "new_issues": [
    {"description": "<a new issue you observed>", "category": "fluency|clarity|vocabulary|grammar|confidence|general", "severity": "low|medium|high"}
  ]
}
If there are no prior issues, return an empty prior_issue_verdicts list. If \
there are no new issues, return an empty new_issues list."""


def _build_user_content(transcript: str, prior_issues: list[dict]) -> str:
    if prior_issues:
        prior = "\n".join(f"- {i['description']}" for i in prior_issues)
    else:
        prior = "(none - this is the first session)"
    return f"Prior open issues:\n{prior}\n\nTranscript:\n{transcript}"


def _parse(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_RE.search(raw)
        if match:
            return json.loads(match.group(0))
        raise


def analyze(transcript: str, prior_issues: list[dict] | None = None) -> Analysis:
    """Run the structured analysis, retrying on invalid output."""
    prior_issues = prior_issues or []
    llm = ChatOllama(
        model=settings.voice_model,
        base_url=settings.ollama_host,
        format="json",
        temperature=0,
    )
    user_content = _build_user_content(transcript, prior_issues)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = llm.invoke(messages).content
            return validate_llm_payload(_parse(raw), prior_issues)
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            last_error = e
            logger.warning("analyze attempt %d failed validation: %s", attempt, e)
        except Exception as e:  # network / model errors - don't keep retrying
            logger.exception("analyze call failed")
            last_error = e
            break

    logger.error("analyze failed after retries; returning empty analysis (%s)", last_error)
    return Analysis(summary="Analysis could not be completed reliably. Please try again.")
