import sys
import types

from app.models import AnalyzeRequest, EvidenceSnippet
from app.services.llm import generate_grounded_bullets_with_llm


class FakeResponse:
    output_text = (
        '{"bullets":[{"evidence_keyword":"FastAPI","evidence_source":"resume",'
        '"evidence_snippet":"Built FastAPI services.","rewritten_bullet":'
        '"基于 FastAPI 服务开发经验，交付面向业务场景的后端能力；投递前请补充真实量化指标。"}]}'
    )


class FakeResponses:
    def create(self, model: str, input: str) -> FakeResponse:
        assert model == "test-model"
        assert "Evidence" in input
        return FakeResponse()


class FakeOpenAIClient:
    responses = FakeResponses()


class FakeMessage:
    content = (
        '{"bullets":[{"evidence_keyword":"LangGraph","evidence_source":"supplemental_materials",'
        '"evidence_snippet":"Designed LangGraph workflows.","rewritten_bullet":'
        '"基于 LangGraph 多节点工作流设计经验，沉淀可扩展的 Agent 编排能力；投递前请补充真实量化指标。"}]}'
    )


class FakeChoice:
    message = FakeMessage()


class FakeChatResponse:
    choices = [FakeChoice()]


class FakeChatCompletions:
    def create(self, model: str, messages: list[dict[str, str]], stream: bool) -> FakeChatResponse:
        assert model == "deepseek-test"
        assert stream is False
        assert messages[0]["role"] == "system"
        return FakeChatResponse()


class FakeChat:
    completions = FakeChatCompletions()


class FakeDeepSeekClient:
    chat = FakeChat()


def test_generate_grounded_bullets_with_mocked_openai(monkeypatch) -> None:
    fake_openai_module = types.SimpleNamespace(OpenAI=lambda **kwargs: FakeOpenAIClient())
    monkeypatch.setitem(sys.modules, "openai", fake_openai_module)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("USE_LLM", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    bullets = generate_grounded_bullets_with_llm(
        AnalyzeRequest(
            resume_text="Built FastAPI services.",
            job_description="Need FastAPI experience.",
        ),
        [
            EvidenceSnippet(
                keyword="FastAPI",
                source="resume",
                snippet="Built FastAPI services.",
                relevance_score=1.0,
            )
        ],
    )

    assert bullets
    assert bullets[0].grounded is True
    assert bullets[0].evidence_keyword == "FastAPI"


def test_generate_grounded_bullets_with_mocked_deepseek(monkeypatch) -> None:
    fake_openai_module = types.SimpleNamespace(OpenAI=lambda **kwargs: FakeDeepSeekClient())
    monkeypatch.setitem(sys.modules, "openai", fake_openai_module)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("USE_LLM", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-test")

    bullets = generate_grounded_bullets_with_llm(
        AnalyzeRequest(
            resume_text="Designed LangGraph workflows.",
            job_description="Need LangGraph experience.",
        ),
        [
            EvidenceSnippet(
                keyword="LangGraph",
                source="supplemental_materials",
                snippet="Designed LangGraph workflows.",
                relevance_score=1.0,
            )
        ],
    )

    assert bullets
    assert bullets[0].grounded is True
    assert bullets[0].evidence_source == "supplemental_materials"


def test_generate_grounded_bullets_returns_none_without_llm(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("USE_LLM", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    bullets = generate_grounded_bullets_with_llm(
        AnalyzeRequest(
            resume_text="Built FastAPI services.",
            job_description="Need FastAPI experience.",
        ),
        [
            EvidenceSnippet(
                keyword="FastAPI",
                source="resume",
                snippet="Built FastAPI services.",
                relevance_score=1.0,
            )
        ],
    )

    assert bullets is None
