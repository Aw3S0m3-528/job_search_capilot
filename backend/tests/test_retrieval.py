from app.models import AnalyzeRequest
from app.services.retrieval import retrieve_resume_evidence


def test_retrieve_resume_evidence_returns_grounded_snippets() -> None:
    request = AnalyzeRequest(
        resume_text=(
            "我使用 FastAPI 构建过生产级后端服务。"
            "我还用 Docker 和 Postgres 部署过 RAG 原型。"
        ),
        job_description="需要 FastAPI、Docker 和 RAG 经验。",
    )

    evidence = retrieve_resume_evidence(request, ["FastAPI", "Docker", "RAG"])

    assert evidence
    assert evidence[0].source == "resume"
    assert any(item.keyword == "FastAPI" for item in evidence)


def test_retrieve_evidence_uses_supplemental_materials() -> None:
    request = AnalyzeRequest(
        resume_text="我是一名后端工程师，主要使用 Python 构建 API。",
        job_description="需要 LangGraph 和 Agent 工作流经验。",
        supplemental_materials=(
            "项目经历：使用 LangGraph 设计多节点 Agent 工作流，"
            "包含需求提取、证据检索、评分和人工审核节点。"
        ),
    )

    evidence = retrieve_resume_evidence(request, ["LangGraph", "Agent"])

    assert evidence
    assert any(item.source == "supplemental_materials" for item in evidence)
    assert any(item.keyword == "LangGraph" for item in evidence)
