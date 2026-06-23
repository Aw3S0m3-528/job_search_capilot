from app.models import JobResearchRequest
from app.services import job_research


def build_request() -> JobResearchRequest:
    return JobResearchRequest(
        company="Acme AI",
        role_title="AI Agent Engineer",
        job_description=(
            "Need Python, FastAPI, LangGraph, RAG, evaluation, and production API experience."
        ),
        resume_text="Built FastAPI and LangGraph agent workflows with parsing evaluation.",
        supplemental_materials="Portfolio project includes OCR, LLM cleaning, and parsing metrics.",
    )


def test_research_job_falls_back_without_search_key(monkeypatch) -> None:
    monkeypatch.setattr(job_research, "tavily_api_key", lambda: "")

    response = job_research.research_job(build_request())

    assert response.used_search is False
    assert response.sources == []
    assert any("TAVILY_API_KEY" in warning for warning in response.warnings)
    assert response.role_signals
    assert response.resume_positioning_advice


class FakeSearchResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "results": [
                {
                    "title": "Acme AI launches enterprise agent platform",
                    "url": "https://example.com/acme-agent-platform",
                    "content": (
                        "Acme AI is hiring engineers for Python, FastAPI, LangGraph, RAG, "
                        "evaluation, and enterprise workflow automation."
                    ),
                    "score": 0.82,
                }
            ]
        }


def test_research_job_returns_llm_structured_advice(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    def fake_post(url: str, headers: dict[str, str], json: dict[str, object], timeout: int):
        captured_payload["url"] = url
        captured_payload["headers"] = headers
        captured_payload["json"] = json
        captured_payload["timeout"] = timeout
        return FakeSearchResponse()

    monkeypatch.setattr(job_research, "tavily_api_key", lambda: "test-tavily-key")
    monkeypatch.setattr(job_research, "tavily_endpoint", lambda: "https://api.tavily.com/search")
    monkeypatch.setattr(job_research.httpx, "post", fake_post)
    monkeypatch.setattr(
        job_research,
        "complete_text",
        lambda prompt: (
            '{"research_summary":"Acme AI is expanding agent workflow products.",'
            '"company_signals":["Enterprise agent platform"],'
            '"role_signals":["Python and LangGraph production work"],'
            '"resume_positioning_advice":["Lead with OCR and evaluation metrics."],'
            '"interview_strategy":["Prepare a source-grounded RAG system walkthrough."],'
            '"resume_rewrite_suggestions":["Rewrite the project section around OCR metrics."],'
            '"cover_letter_draft":"I am applying for this AI Agent role with FastAPI, '
            'LangGraph, OCR, and evaluation project experience."}'
        ),
    )

    response = job_research.research_job(build_request())

    assert response.used_search is True
    assert response.sources[0].url == "https://example.com/acme-agent-platform"
    assert response.company_signals == ["Enterprise agent platform"]
    assert response.resume_positioning_advice == ["Lead with OCR and evaluation metrics."]
    assert response.resume_rewrite_suggestions == [
        "Rewrite the project section around OCR metrics."
    ]
    assert response.cover_letter_draft
    assert response.llm_validation_status == "validated"
    assert response.llm_json_repaired is False
    assert captured_payload["url"] == "https://api.tavily.com/search"
    assert captured_payload["headers"] == {"Authorization": "Bearer test-tavily-key"}
    assert captured_payload["json"]["max_results"] == 6


def test_research_job_repairs_invalid_llm_json(monkeypatch) -> None:
    calls: list[str] = []

    def fake_post(url: str, headers: dict[str, str], json: dict[str, object], timeout: int):
        return FakeSearchResponse()

    def fake_complete(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return "Here is the answer: company is expanding agent work."
        return (
            '{"research_summary":"Acme AI is expanding agent workflow products.",'
            '"company_signals":["Enterprise agent platform"],'
            '"role_signals":["Python and LangGraph production work"],'
            '"resume_positioning_advice":["Lead with OCR and evaluation metrics."],'
            '"interview_strategy":["Prepare a source-grounded RAG system walkthrough."],'
            '"resume_rewrite_suggestions":["Rewrite the project section around OCR metrics."],'
            '"cover_letter_draft":"I am applying for this AI Agent role with FastAPI, '
            'LangGraph, OCR, and evaluation project experience."}'
        )

    monkeypatch.setattr(job_research, "tavily_api_key", lambda: "test-tavily-key")
    monkeypatch.setattr(job_research, "tavily_endpoint", lambda: "https://api.tavily.com/search")
    monkeypatch.setattr(job_research.httpx, "post", fake_post)
    monkeypatch.setattr(job_research, "complete_text", fake_complete)

    response = job_research.research_job(build_request())

    assert response.used_search is True
    assert response.llm_validation_status == "repaired"
    assert response.llm_json_repaired is True
    assert len(calls) == 2
    assert any("自动修复" in warning for warning in response.warnings)
