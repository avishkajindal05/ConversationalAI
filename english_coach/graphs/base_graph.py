# ─── graphs/base_graph.py ───
"""Abstract base graph for LangGraph workflows."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from english_coach.core.logger import logger


def timed_node(name: str, fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Wrap a graph node so its wall-clock time is logged on every run."""

    def _wrapped(state: Any) -> Any:
        start = time.perf_counter()
        try:
            return fn(state)
        finally:
            elapsed = time.perf_counter() - start
            logger.info("node %-22s took %6.1fs", name, elapsed)

    return _wrapped


class BaseGraph(ABC):
    """Abstract base class for all LangGraph workflows."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._graph = None

    @abstractmethod
    def build_graph(self) -> Any:
        """Build and return the compiled LangGraph graph."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
