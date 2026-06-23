from __future__ import annotations

import json
import logging

import httpx
from pydantic import BaseModel, ValidationError

from app.config import tavily_api_key, tavily_endpoint
from app.models import JobResearchRequest, JobResearchResponse, ResearchSource
from app.services.llm import complete_text
from app.services.text import extract_keywords

logger = logging.getLogger(__name__)


class ResearchLLMOutput(BaseModel):
    research_summary: str
    company_signals: list[str]
    role_signals: list[str]
    resume_positioning_advice: list[str]
    interview_strategy: list[str]
    resume_rewrite_suggestions: list[str]
    cover_letter_draft: str


def research_job(request: JobResearchRequest) -> JobResearchResponse:
    warnings: list[str] = []
    sources = search_recent_sources(request, warnings)
    ranked_sources = rank_sources(request, sources)[:6]

    if not ranked_sources:
        warnings.append("未获取到网络资料，已返回基于 JD 的本地建议。")
        return local_research_fallback(request, warnings)

    llm_response, validation_status, repaired = generate_research_with_llm(
        request, ranked_sources, warnings
    )
    if llm_response:
        return JobResearchResponse(
            **llm_response,
            sources=ranked_sources,
            used_search=True,
            llm_validation_status=validation_status,
            llm_json_repaired=repaired,
            warnings=warnings,
        )

    warnings.append("LLM 研究建议生成失败，已返回检索摘要。")
    return source_summary_fallback(request, ranked_sources, warnings)


def search_recent_sources(
    request: JobResearchRequest, warnings: list[str]
) -> list[ResearchSource]:
    api_key = tavily_api_key()
    if not api_key:
        warnings.append("未配置 TAVILY_API_KEY，无法获取网络时效资料。")
        return []

    query = build_search_query(request)
    try:
        response = httpx.post(
            tavily_endpoint(),
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "query": query,
                "search_depth": "basic",
                "topic": "general",
                "time_range": "year",
                "max_results": 6,
                "include_answer": False,
                "include_raw_content": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return [
            ResearchSource(
                title=item.get("title") or "Untitled",
                url=item.get("url") or "",
                content=item.get("content") or "",
                score=float(item.get("score") or 0),
            )
            for item in payload.get("results", [])
            if item.get("url") and item.get("content")
        ]
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        warnings.append("网络搜索失败，请检查 TAVILY_API_KEY 或网络连接。")
        return []


def build_search_query(request: JobResearchRequest) -> str:
    company = request.company or "目标公司"
    role = request.role_title or "目标岗位"
    jd_keywords = " ".join(extract_keywords(request.job_description, limit=8))
    return f"{company} {role} hiring team product strategy technology stack interview {jd_keywords}"


def rank_sources(
    request: JobResearchRequest, sources: list[ResearchSource]
) -> list[ResearchSource]:
    keywords = set(
        extract_keywords(f"{request.company} {request.role_title} {request.job_description}", 20)
    )

    def score(source: ResearchSource) -> float:
        text = f"{source.title} {source.content}".lower()
        overlap = sum(1 for keyword in keywords if keyword.lower() in text)
        return source.score + overlap * 0.2

    return sorted(sources, key=score, reverse=True)


def generate_research_with_llm(
    request: JobResearchRequest, sources: list[ResearchSource], warnings: list[str]
) -> tuple[dict[str, object] | None, str, bool]:
    raw = complete_text(build_research_prompt(request, sources))
    if not raw:
        return None, "llm_unavailable", False

    parsed = parse_and_validate_research_json(raw)
    if parsed:
        return parsed.model_dump(), "validated", False

    repaired_raw = complete_text(build_json_repair_prompt(raw))
    if repaired_raw:
        repaired = parse_and_validate_research_json(repaired_raw)
        if repaired:
            warnings.append("LLM 首次输出 JSON 不合格，已自动修复为 schema-compliant JSON。")
            return repaired.model_dump(), "repaired", True

    logger.warning("Research JSON validation failed after repair attempt.")
    warnings.append("LLM 输出未通过 JSON schema 校验，已返回检索摘要 fallback。")
    return None, "invalid", False


def build_research_prompt(request: JobResearchRequest, sources: list[ResearchSource]) -> str:
    source_payload = [
        {"title": source.title, "url": source.url, "content": source.content[:900]}
        for source in sources
    ]
    return (
        "你是求职研究 Agent。请只基于给定 sources、JD、简历和补充材料输出建议，"
        "不要编造无来源事实，不要夸大候选人经历。\n"
        "必须只输出合法 JSON，不要 Markdown。字段必须严格包含："
        "research_summary, company_signals, role_signals, resume_positioning_advice, "
        "interview_strategy, resume_rewrite_suggestions, cover_letter_draft。\n"
        "所有 list 字段输出 3-5 条中文建议。cover_letter_draft 输出一段 120-180 字中文求职信草稿，"
        "必须基于候选人已有经历和岗位要求，不要虚构公司、学历、年限或量化结果。\n\n"
        f"Company: {request.company}\n"
        f"Role: {request.role_title}\n"
        f"Job description: {request.job_description}\n"
        f"Resume: {request.resume_text[:1200]}\n"
        f"Supplemental materials: {request.supplemental_materials[:1200]}\n"
        f"Sources: {json.dumps(source_payload, ensure_ascii=False)}"
    )


def parse_and_validate_research_json(raw: str) -> ResearchLLMOutput | None:
    try:
        payload = json.loads(strip_json_fence(raw))
        output = ResearchLLMOutput.model_validate(payload)
        if not output.research_summary.strip() or not output.cover_letter_draft.strip():
            return None
        for field_name in (
            "company_signals",
            "role_signals",
            "resume_positioning_advice",
            "interview_strategy",
            "resume_rewrite_suggestions",
        ):
            values = getattr(output, field_name)
            if not values or not all(isinstance(item, str) and item.strip() for item in values):
                return None
        return output
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        logger.warning("Research JSON validation failed: %s", exc)
        return None


def build_json_repair_prompt(raw: str) -> str:
    return (
        "下面是一个不合格的 LLM 输出。请把它修复成严格合法 JSON，不要 Markdown，不要解释。\n"
        "schema 字段必须严格包含：research_summary:string, company_signals:string[], "
        "role_signals:string[], resume_positioning_advice:string[], interview_strategy:string[], "
        "resume_rewrite_suggestions:string[], cover_letter_draft:string。\n"
        "如果原文缺失某字段，请基于原文语义补成保守、中文、不可夸大的内容。\n\n"
        f"Raw output:\n{raw[:4000]}"
    )


def strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        text = text.removesuffix("```").strip()
    return text


def source_summary_fallback(
    request: JobResearchRequest, sources: list[ResearchSource], warnings: list[str]
) -> JobResearchResponse:
    return JobResearchResponse(
        research_summary=(
            f"已检索到 {len(sources)} 条与 "
            f"{request.company or '目标公司'} / {request.role_title or '目标岗位'} "
            "相关的资料，但 LLM 未能生成结构化建议。"
        ),
        company_signals=[source.title for source in sources[:3]],
        role_signals=extract_keywords(request.job_description, limit=5),
        resume_positioning_advice=[
            "请结合资料摘要，手动补充与岗位最相关的项目证据。"
        ],
        interview_strategy=[
            "优先准备与 JD 高频关键词相关的项目故事，并引用网络资料中的业务方向。"
        ],
        resume_rewrite_suggestions=build_local_resume_rewrite_suggestions(request),
        cover_letter_draft=build_local_cover_letter(request),
        sources=sources,
        used_search=True,
        llm_validation_status="fallback",
        warnings=warnings,
    )


def local_research_fallback(
    request: JobResearchRequest, warnings: list[str]
) -> JobResearchResponse:
    keywords = extract_keywords(request.job_description, limit=8)
    return JobResearchResponse(
        research_summary="当前未启用网络资料检索，因此只基于 JD 给出本地建议。",
        company_signals=[],
        role_signals=keywords[:5],
        resume_positioning_advice=[
            f"围绕 {keyword} 补充有证据支撑的项目经历。" for keyword in keywords[:3]
        ],
        interview_strategy=[
            "准备 2-3 个 STAR 项目故事，覆盖 JD 中最频繁出现的能力要求。",
            "补充量化指标，避免只有职责描述没有结果。",
        ],
        resume_rewrite_suggestions=build_local_resume_rewrite_suggestions(request),
        cover_letter_draft=build_local_cover_letter(request),
        sources=[],
        used_search=False,
        llm_validation_status="not_used",
        warnings=warnings,
    )


def build_local_resume_rewrite_suggestions(request: JobResearchRequest) -> list[str]:
    keywords = extract_keywords(request.job_description, limit=5)
    suggestions = [
        f"在简历项目经历中补充与 {keyword} 相关的真实职责、技术选型和结果。"
        for keyword in keywords[:3]
    ]
    suggestions.append("把 Agent、OCR、LLM 清洗、评估指标等项目模块拆成可扫描的 bullet。")
    suggestions.append("所有量化结果只写真实数据；没有数据时保留“可补充指标”提示。")
    return suggestions[:5]


def build_local_cover_letter(request: JobResearchRequest) -> str:
    company = request.company or "贵公司"
    role = request.role_title or "目标岗位"
    keywords = "、".join(extract_keywords(request.job_description, limit=4))
    return (
        f"您好，我希望申请 {company} 的 {role}。我的项目经历集中在 FastAPI、LangGraph、RAG、"
        f"OCR 与 LLM 清洗等方向，能够围绕 {keywords or '岗位要求'} 交付可验证的 AI 工具。"
        "我重视证据约束、评估指标和工程落地，已在求职 Copilot 项目中实现简历解析、岗位匹配、"
        "联网研究和历史记录等能力。期待有机会进一步交流我如何把这些经验用于该岗位。"
    )
