from app.models import AnalyzeRequest
from app.services.scoring import analyze_locally


def test_analyze_locally_returns_fit_report() -> None:
    response = analyze_locally(
        AnalyzeRequest(
            resume_text=(
                "Python backend engineer with FastAPI, React, Docker, Postgres, "
                "RAG, and AI agent project experience. Improved latency by 35%."
            ),
            job_description=(
                "We need a Python AI engineer with FastAPI, LangGraph, RAG, "
                "Postgres, Docker, and production API experience."
            ),
            company="ExampleCo",
            role_title="AI Engineer",
        )
    )

    assert response.match_score > 50
    assert "Python" in response.matched_keywords
    assert response.evidence_snippets
    assert response.tailored_bullets
    assert any(bullet.grounded for bullet in response.tailored_bullets)
    assert response.interview_questions


def test_bullets_mark_unsupported_claims_as_not_grounded() -> None:
    response = analyze_locally(
        AnalyzeRequest(
            resume_text="I have general backend engineering experience with Python APIs.",
            job_description="We need LangGraph, Kubernetes, and payment risk modeling experience.",
        )
    )

    assert response.tailored_bullets
    assert any(not bullet.grounded for bullet in response.tailored_bullets)
    assert any("证据不足" in bullet.original_focus for bullet in response.tailored_bullets)
