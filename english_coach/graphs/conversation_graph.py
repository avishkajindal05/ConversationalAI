# ─── graphs/conversation_graph.py ───
"""LangGraph workflow for the conversation loop.

Each invocation handles exactly one turn:

    (turn 0 only) Greeting -> Difficulty Planner -> Conversation Agent -> Memory Manager
    (turn N)                  Difficulty Planner -> Conversation Agent -> Memory Manager

The caller (the API layer) is responsible for invoking the graph once per
user turn and persisting/reusing the returned SessionState between calls.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from english_coach.agents.conversation.conversation_agent import ConversationAgent
from english_coach.agents.conversation.greeting import GreetingAgent
from english_coach.agents.conversation.memory import MemoryManager
from english_coach.agents.conversation.planner import DifficultyPlanner
from english_coach.graphs.base_graph import BaseGraph, timed_node
from english_coach.memory.session_state import SessionState


class ConversationGraph(BaseGraph):
    """Graph that orchestrates the conversation flow."""

    def __init__(self) -> None:
        super().__init__(name="conversation")
        self.greeting = GreetingAgent()
        self.planner = DifficultyPlanner()
        self.agent = ConversationAgent()
        self.memory = MemoryManager()

    def build_graph(self) -> Any:
        """Build the conversation graph."""
        workflow = StateGraph(SessionState)

        workflow.add_node("greeting_node", timed_node("greeting", self.greeting.run))
        workflow.add_node("planner_node", timed_node("planner", self.planner.run))
        workflow.add_node("conversation_node", timed_node("conversation", self.agent.run))
        workflow.add_node("memory_node", timed_node("memory", self.memory.run))

        workflow.add_conditional_edges(
            START,
            self._route_start,
            {"greeting_node": "greeting_node", "planner_node": "planner_node"},
        )
        workflow.add_edge("greeting_node", "planner_node")
        workflow.add_edge("planner_node", "conversation_node")
        workflow.add_edge("conversation_node", "memory_node")
        workflow.add_edge("memory_node", END)

        self._graph = workflow.compile()
        return self._graph

    @staticmethod
    def _route_start(state: SessionState) -> str:
        """Only run the Greeting Agent on the first turn of a session."""
        return "greeting_node" if state.conversation.turn_count == 0 else "planner_node"
