from __future__ import annotations

from typing import TypedDict

from app.models import AnalyzeRequest, AnalyzeResponse, EvidenceSnippet, ResumeBullet, SkillGap
from app.services.retrieval import retrieve_resume_evidence
from app.services.scoring import (
    build_interview_questions,
    build_next_actions,
    build_skill_gaps,
    build_summary,
    build_tailored_bullets,
    calculate_score,
    compare_keywords,
    extract_job_keywords,
    extract_resume_keywords,
)


class JobMatchState(TypedDict, total=False):
    request: AnalyzeRequest
    resume_keywords: set[str]
    job_keywords: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    evidence_snippets: list[EvidenceSnippet]
    match_score: int
    skill_gaps: list[SkillGap]
    tailored_bullets: list[ResumeBullet]
    interview_questions: list[str]
    summary: str
    response: AnalyzeResponse


def extract_requirements(state: JobMatchState) -> JobMatchState:
    request = state["request"]
    return {
        **state,
        "resume_keywords": extract_resume_keywords(request),
        "job_keywords": extract_job_keywords(request),
    }


def compare_candidate_evidence(state: JobMatchState) -> JobMatchState:
    matched, missing = compare_keywords(state["resume_keywords"], state["job_keywords"])
    evidence = retrieve_resume_evidence(state["request"], matched[:12])
    return {
        **state,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "evidence_snippets": evidence,
    }


def score_fit(state: JobMatchState) -> JobMatchState:
    score = calculate_score(state["matched_keywords"], state["job_keywords"])
    return {**state, "match_score": score}


def identify_gaps(state: JobMatchState) -> JobMatchState:
    return {**state, "skill_gaps": build_skill_gaps(state["missing_keywords"])}


def draft_resume_bullets(state: JobMatchState) -> JobMatchState:
    request = state["request"]
    return {
        **state,
        "tailored_bullets": build_tailored_bullets(
            request,
            state["matched_keywords"][:5],
            state["missing_keywords"][:3],
            state["evidence_snippets"],
        ),
    }


def generate_interview_plan(state: JobMatchState) -> JobMatchState:
    request = state["request"]
    return {
        **state,
        "interview_questions": build_interview_questions(
            request,
            state["matched_keywords"][:4],
            state["missing_keywords"][:4],
        ),
    }


def assemble_final_report(state: JobMatchState) -> JobMatchState:
    request = state["request"]
    summary = build_summary(
        request,
        state["match_score"],
        state["matched_keywords"],
        state["missing_keywords"],
    )
    response = AnalyzeResponse(
        match_score=state["match_score"],
        summary=summary,
        matched_keywords=state["matched_keywords"][:12],
        missing_keywords=state["missing_keywords"],
        evidence_snippets=state["evidence_snippets"],
        skill_gaps=state["skill_gaps"],
        tailored_bullets=state["tailored_bullets"],
        interview_questions=state["interview_questions"],
        next_actions=build_next_actions(),
    )
    return {**state, "summary": summary, "response": response}


def run_sequential_workflow(request: AnalyzeRequest) -> AnalyzeResponse:
    state: JobMatchState = {"request": request}
    for node in (
        extract_requirements,
        compare_candidate_evidence,
        score_fit,
        identify_gaps,
        draft_resume_bullets,
        generate_interview_plan,
        assemble_final_report,
    ):
        state = node(state)
    return state["response"]


def run_job_match_workflow(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run the job-match agent workflow.

    The workflow is intentionally split into small LangGraph nodes. The current nodes
    use deterministic local logic, and each node can later be replaced with LlamaIndex
    retrieval, OpenAI Agents SDK calls, or human review checkpoints.
    """
    try:
        from langgraph.graph import END, StateGraph
    except Exception:
        return run_sequential_workflow(request)

    graph = StateGraph(JobMatchState)
    graph.add_node("extract_requirements", extract_requirements)
    graph.add_node("compare_candidate_evidence", compare_candidate_evidence)
    graph.add_node("score_fit", score_fit)
    graph.add_node("identify_gaps", identify_gaps)
    graph.add_node("draft_resume_bullets", draft_resume_bullets)
    graph.add_node("generate_interview_plan", generate_interview_plan)
    graph.add_node("assemble_final_report", assemble_final_report)

    graph.set_entry_point("extract_requirements")
    graph.add_edge("extract_requirements", "compare_candidate_evidence")
    graph.add_edge("compare_candidate_evidence", "score_fit")
    graph.add_edge("score_fit", "identify_gaps")
    graph.add_edge("identify_gaps", "draft_resume_bullets")
    graph.add_edge("draft_resume_bullets", "generate_interview_plan")
    graph.add_edge("generate_interview_plan", "assemble_final_report")
    graph.add_edge("assemble_final_report", END)

    app = graph.compile()
    result = app.invoke({"request": request})
    return result["response"]
