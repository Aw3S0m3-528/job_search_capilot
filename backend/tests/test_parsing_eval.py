from pathlib import Path

from app.services.parsing_eval import (
    ResumeEvalSpec,
    diagnose_resume_parse,
    evaluate_resume_parse,
    load_eval_spec,
    truncation_risk,
)


def test_evaluate_resume_parse_scores_expected_fields() -> None:
    result = evaluate_resume_parse(
        ResumeEvalSpec(
            sample_id="unit",
            expected_text="技能 Python FastAPI 项目经历 LangGraph",
            parsed_text="技能 Python FastAPI 项目经历",
            required_keywords=["Python", "FastAPI", "LangGraph"],
            required_sections=["技能", "项目经历"],
        )
    )

    assert result["keyword_recall"] == 0.6667
    assert result["section_recall"] == 1.0
    assert result["parsed_chars"] > 0


def test_truncation_risk_detects_short_parse() -> None:
    assert truncation_risk("技能 Python", "技能 Python 项目经历 LangGraph RAG Postgres Docker")


def test_load_eval_spec_from_fixture() -> None:
    fixture = Path("fixtures/resume_parsing/sample_01")
    spec = load_eval_spec(fixture)

    assert spec.sample_id == "sample_01"
    assert "FastAPI" in spec.expected_text
    assert "项目经历" in spec.required_sections


def test_diagnose_resume_parse_reports_missing_keywords() -> None:
    diagnostics = diagnose_resume_parse(
        ResumeEvalSpec(
            sample_id="unit",
            expected_text="技能 Python FastAPI LangGraph 项目经历 最终项目",
            parsed_text="技能 Python 项目经历",
            required_keywords=["Python", "FastAPI", "LangGraph"],
            required_sections=["技能", "项目经历"],
        )
    )

    assert diagnostics["missing_keywords"] == ["FastAPI", "LangGraph"]
    assert diagnostics["missing_sections"] == []
