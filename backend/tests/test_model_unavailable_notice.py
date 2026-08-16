import asyncio
import json
import os
import unittest
from unittest.mock import MagicMock, patch

import httpx
import openai

os.environ.setdefault("RAGFLOW_API_KEY", "test")
os.environ.setdefault("RAGFLOW_BASE_URL", "http://localhost")
os.environ.setdefault("RAGFLOW_AGENT_ID", "test")
os.environ.setdefault("RAGFLOW_CHAT_ID", "test")
os.environ.setdefault("RAGFLOW_DATASET_ID", "test")
os.environ.setdefault("RAGFLOW_PUBLIC_DATASET_IDS", "")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_API_BASE", "http://localhost")

from app.api.endpoints.chat import (
    build_model_unavailable_event,
    is_configured_model_unavailable,
    is_model_invocation_error,
    stream_chat_events,
)
from app.schemas.chat import ChatRequest


def _connection_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(request=httpx.Request("POST", "https://example.com/v1/chat/completions"))


class StubAgentGraph:
    def __init__(self, events):
        self.events = events
        self.captured_config = None

    async def astream_events(self, state, config=None, version="v1"):
        self.captured_config = config
        for event in self.events:
            if isinstance(event, Exception):
                raise event
            yield event


def _token_event(text="answer"):
    return {"event": "on_chat_model_stream", "data": {"chunk": MagicMock(content=text)}}


async def _collect_stream_events(request):
    events = []
    with patch("app.api.endpoints.chat.save_chat_message"), \
         patch("app.api.endpoints.chat.query_data_structure_knowledge") as rag_tool, \
         patch("app.services.profile_extractor.extract_and_update_profile", new=lambda *a, **k: asyncio.sleep(0)):
        rag_tool.invoke.return_value = "RAG fallback content"
        async for sse_line in stream_chat_events(request, MagicMock()):
            events.append(json.loads(sse_line[len("data: "):]))
    return events


class ModelUnavailableHelperTest(unittest.TestCase):
    def test_is_model_invocation_error_matches_openai_errors_only(self):
        self.assertTrue(is_model_invocation_error(_connection_error()))
        self.assertTrue(issubclass(openai.AuthenticationError, openai.OpenAIError))
        self.assertFalse(is_model_invocation_error(ValueError("boom")))
        self.assertFalse(is_model_invocation_error(RuntimeError("boom")))

    def test_is_configured_model_unavailable(self):
        request = ChatRequest(message="hi", agent_model="mimo-v2.5")
        self.assertTrue(is_configured_model_unavailable(request))
        request = ChatRequest(message="hi", agent_model="kimi-k2.6")
        self.assertFalse(is_configured_model_unavailable(request))
        request = ChatRequest(message="hi")
        self.assertFalse(is_configured_model_unavailable(request))

    def test_build_model_unavailable_event_payload(self):
        payload = json.loads(build_model_unavailable_event("mimo-v2.5")[len("data: "):])
        self.assertEqual(payload["type"], "model_unavailable")
        self.assertEqual(payload["model"], "mimo-v2.5")
        self.assertIn("请更换模型", payload["message"])


class StreamModelUnavailableTest(unittest.TestCase):
    def test_unregistered_configured_model_emits_model_unavailable(self):
        stub = StubAgentGraph([_token_event()])
        with patch("app.api.endpoints.chat.agent_graph", stub):
            events = asyncio.run(_collect_stream_events(ChatRequest(message="hi", agent_model="mimo-v2.5")))

        notice_events = [e for e in events if e["type"] == "model_unavailable"]
        self.assertEqual(len(notice_events), 1)
        self.assertEqual(notice_events[0]["model"], "mimo-v2.5")
        self.assertIn("请更换模型", notice_events[0]["message"])
        # 回退默认模型后仍正常作答
        self.assertEqual(stub.captured_config["configurable"]["agent_model"], "qwen3.7-plus")
        self.assertTrue(any(e["type"] == "token" for e in events))
        self.assertTrue(any(e["type"] == "complete" for e in events))

    def test_model_invocation_error_emits_notice_and_keeps_rag_fallback(self):
        stub = StubAgentGraph([_connection_error()])
        with patch("app.api.endpoints.chat.agent_graph", stub):
            events = asyncio.run(_collect_stream_events(ChatRequest(message="hi", agent_model="kimi-k2.6")))

        notice_events = [e for e in events if e["type"] == "model_unavailable"]
        self.assertEqual(len(notice_events), 1)
        self.assertEqual(notice_events[0]["model"], "kimi-k2.6")
        fallback_tokens = [e for e in events if e["type"] == "token"]
        self.assertTrue(fallback_tokens)
        self.assertIn("RAGFlow", fallback_tokens[0]["content"])
        self.assertTrue(any(e["type"] == "complete" for e in events))

    def test_non_model_error_does_not_emit_notice(self):
        stub = StubAgentGraph([ValueError("tool failure")])
        with patch("app.api.endpoints.chat.agent_graph", stub):
            events = asyncio.run(_collect_stream_events(ChatRequest(message="hi", agent_model="kimi-k2.6")))

        self.assertFalse(any(e["type"] == "model_unavailable" for e in events))

    def test_valid_model_streams_without_notice(self):
        stub = StubAgentGraph([_token_event()])
        with patch("app.api.endpoints.chat.agent_graph", stub):
            events = asyncio.run(_collect_stream_events(ChatRequest(message="hi", agent_model="kimi-k2.6")))

        self.assertFalse(any(e["type"] == "model_unavailable" for e in events))
        self.assertTrue(any(e["type"] == "token" for e in events))


if __name__ == "__main__":
    unittest.main()
