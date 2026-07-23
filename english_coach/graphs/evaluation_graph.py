# ─── graphs/evaluation_graph.py ───
"""LangGraph workflow for the evaluation pipeline.

Runs once, after a session ends, over the full transcript. The five scoring
agents are independent and fan out in parallel; Recommendation and Report
depend on all of them and run sequentially at the fan-in:

    START ─┬─ Grammar ────┐
           ├─ Vocabulary ─┤
           ├─ Fluency ────┼─▶ Recommendation ─▶ Report ─▶ END
           ├─ Engagement ─┤
           └─ Confidence ─┘

(On a single-GPU/CPU host Ollama may still serialize the calls, but the graph
is now ready to exploit real parallelism given the hardware or extra model
instances. Concurrent writes merge via the SessionState.scores reducer.)
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from english_coach.agents.evaluation.confidence import ConfidenceAgent
from english_coach.agents.evaluation.engagement import EngagementAgent
from english_coach.agents.evaluation.fluency import FluencyAgent
from english_coach.agents.evaluation.grammar import GrammarAgent
from english_coach.agents.evaluation.recommendation import RecommendationAgent
from english_coach.agents.evaluation.report import ReportAgent
from english_coach.agents.evaluation.vocabulary import VocabularyAgent
from english_coach.graphs.base_graph import BaseGraph, timed_node
from english_coach.memory.session_state import SessionState


class EvaluationGraph(BaseGraph):
    """Graph that orchestrates the post-session evaluation flow."""

    def __init__(self) -> None:
        super().__init__(name="evaluation")
        self.grammar = GrammarAgent()
        self.vocabulary = VocabularyAgent()
        self.fluency = FluencyAgent()
        self.engagement = EngagementAgent()
        self.confidence = ConfidenceAgent()
        self.recommendation = RecommendationAgent()
        self.report = ReportAgent()

    def build_graph(self) -> Any:
        """Build the evaluation graph."""
        workflow = StateGraph(SessionState)

        workflow.add_node("grammar_node", timed_node("grammar", self.grammar.run))
        workflow.add_node("vocabulary_node", timed_node("vocabulary", self.vocabulary.run))
        workflow.add_node("fluency_node", timed_node("fluency", self.fluency.run))
        workflow.add_node("engagement_node", timed_node("engagement", self.engagement.run))
        workflow.add_node("confidence_node", timed_node("confidence", self.confidence.run))
        workflow.add_node("recommendation_node", timed_node("recommendation", self.recommendation.run))
        workflow.add_node("report_node", timed_node("report", self.report.run))

        scoring_nodes = [
            "grammar_node",
            "vocabulary_node",
            "fluency_node",
            "engagement_node",
            "confidence_node",
        ]
        # Fan-out: all five scorers start together.
        for node in scoring_nodes:
            workflow.add_edge(START, node)
        # Fan-in: recommendation waits for every scorer to finish.
        for node in scoring_nodes:
            workflow.add_edge(node, "recommendation_node")
        workflow.add_edge("recommendation_node", "report_node")
        workflow.add_edge("report_node", END)

        self._graph = workflow.compile()
        return self._graph
