from app.models import AnalyzeRequest
from app.workflow import (
    compare_candidate_evidence,
    extract_requirements,
    run_sequential_workflow,
)


def build_request() -> AnalyzeRequest:
    return AnalyzeRequest(
        resume_text=(
            "Python 后端工程师，熟悉 FastAPI、React、Docker、Postgres 和 AI Agent 项目开发。"
            "曾为内部知识库构建 RAG 原型，并将 API 延迟降低 35%。"
        ),
        job_description=(
            "我们正在招聘 AI 工程师，需要 Python、FastAPI、LangGraph、RAG、"
            "Postgres、Docker 和生产级 API 经验。"
        ),
        company="ExampleCo",
        role_title="AI 工程师",
    )


def test_workflow_extracts_requirements_and_evidence() -> None:
    state = extract_requirements({"request": build_request()})
    state = compare_candidate_evidence(state)

    assert "Python" in state["job_keywords"]
    assert "Python" in state["matched_keywords"]
    assert "LangGraph" in state["missing_keywords"]
    assert state["evidence_snippets"]


def test_sequential_workflow_returns_chinese_report() -> None:
    response = run_sequential_workflow(build_request())

    assert response.match_score > 50
    assert "你的候选人资料" in response.summary
    assert response.evidence_snippets
    assert response.skill_gaps
    assert response.tailored_bullets
    assert any(bullet.grounded for bullet in response.tailored_bullets)
    assert response.interview_questions


def test_workflow_matches_keywords_from_supplemental_materials() -> None:
    response = run_sequential_workflow(
        AnalyzeRequest(
            resume_text="我是一名后端工程师，主要使用 Python 构建 API。",
            job_description="需要 LangGraph 和 Agent 工作流经验。",
            supplemental_materials=(
                "项目经历：使用 LangGraph 设计多节点 Agent 工作流，"
                "包含需求提取、证据检索、评分和人工审核节点。"
            ),
        )
    )

    assert "LangGraph" in response.matched_keywords
    assert any(item.source == "supplemental_materials" for item in response.evidence_snippets)
    assert any(bullet.evidence_source == "supplemental_materials" for bullet in response.tailored_bullets)
