# ─── llm/conversation_model.py ───
"""Conversation LLM wrapper.

Uses the conversation-specific Ollama model for dialogue generation.
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama

from english_coach.core.constants import DEFAULT_LLM_TIMEOUT, LLM_RETRY_ATTEMPTS
from english_coach.core.settings import settings
from english_coach.core.logger import logger


class ConversationModel:
    """Wrapper around the conversation LLM."""

    def __init__(self) -> None:
        self.model_name = settings.conversation_model
        self.host = settings.ollama_host
        self.llm = ChatOllama(
            model=self.model_name,
            base_url=self.host,
            client_kwargs={"timeout": DEFAULT_LLM_TIMEOUT},
        ).with_retry(stop_after_attempt=LLM_RETRY_ATTEMPTS)
        
        # Load system prompt
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "prompts", 
            "conversation", 
            "system.md"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()
        except FileNotFoundError:
            logger.warning("System prompt not found at %s. Using default.", prompt_path)
            self.system_prompt = "You are a friendly English speaking partner."

        logger.info("ConversationModel -> %s @ %s", self.model_name, self.host)

    def respond(self, messages: list[dict[str, Any]], extra_instructions: str = "") -> str:
        """Generate a conversational response.

        Takes a list of dictionaries with 'role' and 'content', injects the
        system prompt (optionally extended with difficulty/topic guidance
        from the Difficulty Planner) at the beginning, and returns the
        response string.
        """
        system_prompt = self.system_prompt
        if extra_instructions:
            system_prompt = f"{system_prompt}\n\n{extra_instructions}"
        lc_messages = [SystemMessage(content=system_prompt)]

        for msg in messages:
            if msg.get("role") == "user":
                lc_messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                lc_messages.append(AIMessage(content=msg.get("content", "")))

        logger.debug("Invoking ChatOllama with %d messages", len(lc_messages))
        try:
            response = self.llm.invoke(lc_messages)
            return response.content
        except Exception:
            logger.exception("ConversationModel call failed after retries.")
            return (
                "Sorry, I had trouble responding just now. "
                "Could you say that again?"
            )
