# ─── llm/evaluation_model.py ───
"""Evaluation LLM wrapper.

Every evaluation agent shares this wrapper but may point it at a different
Ollama model (light scoring model vs. larger reasoning model) and cap its
output length. Calls are retried and time-bounded; on any failure the
agent's fallback dict is returned so one flaky call never crashes the graph.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from english_coach.core.constants import DEFAULT_LLM_TIMEOUT, LLM_RETRY_ATTEMPTS
from english_coach.core.logger import logger
from english_coach.core.settings import settings

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class EvaluationModel:
    """Wrapper around the evaluation LLM."""

    def __init__(self, model_name: str | None = None, num_predict: int | None = None) -> None:
        # Defaults to the lighter scoring model; reasoning-heavy agents
        # (recommendation) pass settings.reasoning_model explicitly.
        self.model_name = model_name or settings.scoring_model
        self.host = settings.ollama_host
        options: dict[str, Any] = {
            "model": self.model_name,
            "base_url": self.host,
            "format": "json",
            "client_kwargs": {"timeout": DEFAULT_LLM_TIMEOUT},
        }
        if num_predict is not None:
            options["num_predict"] = num_predict
        self.llm = ChatOllama(**options).with_retry(
            stop_after_attempt=LLM_RETRY_ATTEMPTS
        )
        logger.info("EvaluationModel -> %s @ %s", self.model_name, self.host)

    def evaluate(self, system_prompt: str, content: str, fallback: dict[str, Any]) -> dict[str, Any]:
        """Run a structured evaluation and parse the model's JSON response.

        `content` is whatever input the agent needs judged - usually the
        conversation transcript, but recommendation/report agents pass a
        compact summary of upstream scores instead.

        `fallback` is returned if the call or JSON parse fails, so a single
        flaky agent never crashes the whole evaluation graph.
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=content),
        ]
        try:
            response = self.llm.invoke(messages)
            return self._parse_json(response.content, fallback)
        except Exception:
            logger.exception("EvaluationModel call failed, using fallback result.")
            return fallback

    @staticmethod
    def _parse_json(raw: str, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = _JSON_BLOCK_RE.search(raw)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            logger.warning("Could not parse evaluation JSON, using fallback. Raw: %s", raw[:200])
            return fallback
