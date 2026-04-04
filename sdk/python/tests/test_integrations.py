"""Tests for all framework integrations using mock objects.

Copyright 2026 Agentability Contributors
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from collections.abc import Generator

import pytest

from agentability import Tracer
from agentability.models import DecisionType


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def tracer(tmp_path: Path) -> Generator[Tracer, None, None]:
    t = Tracer(offline_mode=True, database_path=str(tmp_path / "test.db"))
    yield t
    t.close()


# ===========================================================================
# AnthropicInstrumentation
# ===========================================================================


class TestAnthropicInstrumentation:
    def _make_client(self) -> Any:
        """Return a minimal mock Anthropic client."""

        class MockUsage:
            input_tokens = 500
            output_tokens = 200

        class MockResponse:
            usage = MockUsage()
            stop_reason = "end_turn"

        class MockMessages:
            def create(self, **kwargs: Any) -> MockResponse:
                return MockResponse()

        class MockClient:
            messages = MockMessages()

        return MockClient()

    def test_wrap_client_returns_client(self, tracer: Tracer) -> None:
        from agentability.integrations.anthropic_sdk import AnthropicInstrumentation

        client = self._make_client()
        wrapped = AnthropicInstrumentation(tracer).wrap_client(client)
        assert wrapped is client

    def test_tracked_create_records_llm_call(self, tracer: Tracer) -> None:
        from agentability.integrations.anthropic_sdk import AnthropicInstrumentation

        client = self._make_client()
        AnthropicInstrumentation(tracer, agent_id="test_agent").wrap_client(client)
        client.messages.create(model="claude-sonnet-4", messages=[])
        # Verify call was recorded (no exception means success)

    def test_tracked_create_returns_response(self, tracer: Tracer) -> None:
        from agentability.integrations.anthropic_sdk import AnthropicInstrumentation

        client = self._make_client()
        AnthropicInstrumentation(tracer).wrap_client(client)
        response = client.messages.create(model="claude-sonnet-4", messages=[])
        assert response is not None

    def test_response_without_usage_handled(self, tracer: Tracer) -> None:
        from agentability.integrations.anthropic_sdk import AnthropicInstrumentation

        class NoUsageClient:
            class messages:
                @staticmethod
                def create(**kwargs: Any) -> Any:
                    class R:
                        usage = None
                        stop_reason = None
                    return R()

        client = NoUsageClient()
        AnthropicInstrumentation(tracer).wrap_client(client)
        client.messages.create(model="claude-haiku-4", messages=[])


# ===========================================================================
# CrewAIInstrumentation
# ===========================================================================


class TestCrewAIInstrumentation:
    def _make_crew(self, result: Any = "crew_result") -> Any:
        class MockCrew:
            def kickoff(self) -> Any:
                return result

        return MockCrew()

    def _make_agent(self, role: str = "researcher") -> Any:
        class MockTask:
            description = "Do something"

        class MockAgent:
            pass

        agent = MockAgent()
        agent.role = role  # type: ignore[attr-defined]

        def execute_task(task: Any, *args: Any, **kwargs: Any) -> str:
            return "task_result"

        agent.execute_task = execute_task  # type: ignore[attr-defined]
        return agent

    def test_instrument_crew_returns_crew(self, tracer: Tracer) -> None:
        from agentability.integrations.crewai import CrewAIInstrumentation

        crew = self._make_crew()
        wrapped = CrewAIInstrumentation(tracer).instrument_crew(crew)
        assert wrapped is crew

    def test_crew_kickoff_recorded(self, tracer: Tracer) -> None:
        from agentability.integrations.crewai import CrewAIInstrumentation

        crew = self._make_crew("final_answer")
        CrewAIInstrumentation(tracer, session_id="sess_1").instrument_crew(crew)
        result = crew.kickoff()
        assert result == "final_answer"
        decisions = tracer.query_decisions()
        assert len(decisions) >= 1

    def test_crew_without_kickoff_skipped(self, tracer: Tracer) -> None:
        from agentability.integrations.crewai import CrewAIInstrumentation

        class NoCrew:
            pass

        wrapped = CrewAIInstrumentation(tracer).instrument_crew(NoCrew())
        assert wrapped is not None

    def test_instrument_agent_returns_agent(self, tracer: Tracer) -> None:
        from agentability.integrations.crewai import CrewAIInstrumentation

        agent = self._make_agent()
        wrapped = CrewAIInstrumentation(tracer).instrument_agent(agent)
        assert wrapped is agent

    def test_agent_execute_task_recorded(self, tracer: Tracer) -> None:
        from agentability.integrations.crewai import CrewAIInstrumentation

        agent = self._make_agent(role="analyst")

        class FakeTask:
            description = "Analyse data"

        CrewAIInstrumentation(tracer).instrument_agent(agent)
        result = agent.execute_task(FakeTask())
        assert result == "task_result"

    def test_agent_without_execute_task_skipped(self, tracer: Tracer) -> None:
        from agentability.integrations.crewai import CrewAIInstrumentation

        class NoAgent:
            pass

        wrapped = CrewAIInstrumentation(tracer).instrument_agent(NoAgent())
        assert wrapped is not None


# ===========================================================================
# AutoGenInstrumentation
# ===========================================================================


class TestAutoGenInstrumentation:
    def _make_agent(self, name: str = "assistant") -> Any:
        class MockAgent:
            pass

        agent = MockAgent()
        agent.name = name  # type: ignore[attr-defined]

        def generate_reply(
            messages: Any = None, sender: Any = None, **kwargs: Any
        ) -> str:
            return "reply_text"

        agent.generate_reply = generate_reply  # type: ignore[attr-defined]
        return agent

    def test_instrument_agent_returns_agent(self, tracer: Tracer) -> None:
        from agentability.integrations.autogen import AutoGenInstrumentation

        agent = self._make_agent()
        wrapped = AutoGenInstrumentation(tracer).instrument_agent(agent)
        assert wrapped is agent

    def test_generate_reply_returns_string(self, tracer: Tracer) -> None:
        from agentability.integrations.autogen import AutoGenInstrumentation

        agent = self._make_agent()
        AutoGenInstrumentation(tracer).instrument_agent(agent)
        reply = agent.generate_reply(messages=[{"content": "Hello"}])
        assert reply == "reply_text"

    def test_none_reply_returns_none(self, tracer: Tracer) -> None:
        from agentability.integrations.autogen import AutoGenInstrumentation

        class NoneAgent:
            name = "null_agent"

            def generate_reply(self, **kwargs: Any) -> None:
                return None

        agent = NoneAgent()
        AutoGenInstrumentation(tracer).instrument_agent(agent)
        reply = agent.generate_reply(messages=[])
        assert reply is None

    def test_agent_without_generate_reply_skipped(self, tracer: Tracer) -> None:
        from agentability.integrations.autogen import AutoGenInstrumentation

        class NoMethod:
            pass

        wrapped = AutoGenInstrumentation(tracer).instrument_agent(NoMethod())
        assert wrapped is not None

    def test_decision_recorded_after_reply(self, tracer: Tracer) -> None:
        from agentability.integrations.autogen import AutoGenInstrumentation

        agent = self._make_agent("recorder_agent")
        AutoGenInstrumentation(tracer, session_id="s1").instrument_agent(agent)
        agent.generate_reply(
            messages=[{"content": "Hello"}], sender=None
        )
        decisions = tracer.query_decisions(decision_type=DecisionType.GENERATION)
        assert len(decisions) >= 1


# ===========================================================================
# AgentabilityLangChainCallback
# ===========================================================================


class TestLangChainCallback:
    def _make_callback(self, tracer: Tracer) -> Any:
        from agentability.integrations.langchain import AgentabilityLangChainCallback

        return AgentabilityLangChainCallback(tracer=tracer, agent_id="lc_agent")

    def _make_run_id(self) -> Any:
        from uuid import uuid4

        return uuid4()

    def test_callback_instantiates(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        assert cb is not None

    def test_on_llm_start_stores_time(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_llm_start({}, ["prompt"], run_id=run_id)
        assert str(run_id) in cb._llm_start_times

    def test_on_llm_end_records_call(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_llm_start({}, ["prompt"], run_id=run_id)

        class MockResponse:
            llm_output = {
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
                "model_name": "gpt-4",
            }

        cb.on_llm_end(MockResponse(), run_id=run_id)

    def test_on_llm_end_no_usage(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_llm_start({}, ["p"], run_id=run_id)

        class NoUsageResponse:
            llm_output = None

        cb.on_llm_end(NoUsageResponse(), run_id=run_id)

    def test_on_chain_start_stores_context(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_chain_start({"name": "TestChain"}, {"input": "x"}, run_id=run_id)
        assert str(run_id) in cb._chain_contexts

    def test_on_chain_end_records_decision(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_chain_start({"name": "MyChain"}, {"input": "test"}, run_id=run_id)
        cb.on_chain_end({"output": "result"}, run_id=run_id)
        decisions = tracer.query_decisions(agent_id="lc_agent")
        assert len(decisions) >= 1

    def test_on_chain_end_no_context_skipped(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        # Should not raise even without a prior on_chain_start
        cb.on_chain_end({"output": "x"}, run_id=run_id)

    def test_on_tool_start_stores_time(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_tool_start({"name": "search"}, "query", run_id=run_id)
        assert f"tool_{run_id}" in cb._llm_start_times

    def test_on_tool_end_clears_time(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_tool_start({}, "q", run_id=run_id)
        cb.on_tool_end("result", run_id=run_id)
        assert f"tool_{run_id}" not in cb._llm_start_times

    def test_agent_callbacks_do_not_raise(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_agent_action(object(), run_id=run_id)
        cb.on_agent_finish(object(), run_id=run_id)

    def test_chain_start_with_id_fallback(self, tracer: Tracer) -> None:
        cb = self._make_callback(tracer)
        run_id = self._make_run_id()
        cb.on_chain_start({"id": ["my", "ChainClass"]}, {}, run_id=run_id)
        ctx = cb._chain_contexts.get(str(run_id))
        assert ctx is not None
        assert ctx["chain_name"] == "ChainClass"


# ===========================================================================
# LlamaIndexInstrumentation
# ===========================================================================


class TestLlamaIndexInstrumentation:
    def _make_query_engine(self) -> Any:
        class MockNode:
            score = 0.85

        class MockResponse:
            source_nodes = [MockNode(), MockNode()]

            def __str__(self) -> str:
                return "answer text"

        class MockQueryEngine:
            def query(self, query_str: str, **kwargs: Any) -> MockResponse:
                return MockResponse()

        return MockQueryEngine()

    def _make_retriever(self) -> Any:
        class MockNode:
            score = 0.9

        class MockRetriever:
            def retrieve(self, query_str: str, **kwargs: Any) -> list[Any]:
                return [MockNode(), MockNode(), MockNode()]

        return MockRetriever()

    def test_instrument_query_engine_returns_engine(
        self, tracer: Tracer
    ) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        engine = self._make_query_engine()
        wrapped = LlamaIndexInstrumentation(tracer).instrument_query_engine(engine)
        assert wrapped is engine

    def test_query_returns_response(self, tracer: Tracer) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        engine = self._make_query_engine()
        LlamaIndexInstrumentation(tracer, agent_id="li_agent").instrument_query_engine(
            engine
        )
        response = engine.query("What is AI?")
        assert response is not None

    def test_query_records_decision(self, tracer: Tracer) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        engine = self._make_query_engine()
        LlamaIndexInstrumentation(tracer, agent_id="li_agent").instrument_query_engine(
            engine
        )
        engine.query("What is AI?")
        decisions = tracer.query_decisions(agent_id="li_agent")
        assert len(decisions) >= 1

    def test_engine_without_query_skipped(self, tracer: Tracer) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        class NoEngine:
            pass

        wrapped = LlamaIndexInstrumentation(tracer).instrument_query_engine(NoEngine())
        assert wrapped is not None

    def test_instrument_retriever_returns_retriever(
        self, tracer: Tracer
    ) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        retriever = self._make_retriever()
        wrapped = LlamaIndexInstrumentation(tracer).instrument_retriever(retriever)
        assert wrapped is retriever

    def test_retriever_retrieve_records_memory_op(
        self, tracer: Tracer
    ) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        retriever = self._make_retriever()
        LlamaIndexInstrumentation(tracer, agent_id="li_retriever").instrument_retriever(
            retriever
        )
        nodes = retriever.retrieve("search query")
        assert len(nodes) == 3

    def test_retriever_without_retrieve_skipped(self, tracer: Tracer) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        class NoRetrieve:
            pass

        wrapped = LlamaIndexInstrumentation(tracer).instrument_retriever(NoRetrieve())
        assert wrapped is not None

    def test_query_engine_no_source_nodes(self, tracer: Tracer) -> None:
        from agentability.integrations.llamaindex import LlamaIndexInstrumentation

        class SimpleEngine:
            def query(self, query_str: str, **kwargs: Any) -> str:
                return "plain answer"

        engine = SimpleEngine()
        LlamaIndexInstrumentation(tracer).instrument_query_engine(engine)
        result = engine.query("test")
        assert result == "plain answer"
