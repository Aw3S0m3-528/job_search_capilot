from __future__ import annotations

from app.models import AnalyzeRequest, AnalyzeResponse, EvidenceSnippet, ResumeBullet, SkillGap
from app.services.llm import generate_grounded_bullets_with_llm
from app.services.retrieval import retrieve_resume_evidence
from app.services.text import extract_keywords


def extract_resume_keywords(request: AnalyzeRequest) -> set[str]:
    text = request.resume_text
    if request.supplemental_materials.strip():
        text = f"{text}\n{request.supplemental_materials}"
    return set(extract_keywords(text, limit=60))


def extract_job_keywords(request: AnalyzeRequest) -> list[str]:
    return extract_keywords(request.job_description, limit=32)


def compare_keywords(
    resume_keywords: set[str], job_keywords: list[str]
) -> tuple[list[str], list[str]]:
    matched = [keyword for keyword in job_keywords if keyword in resume_keywords]
    missing = [keyword for keyword in job_keywords if keyword not in resume_keywords][:10]
    return matched, missing


def calculate_score(matched: list[str], job_keywords: list[str]) -> int:
    score = int(min(100, round((len(matched) / max(len(job_keywords), 1)) * 100 + 15)))
    return max(score, 25 if matched else 10)


def build_skill_gaps(missing: list[str]) -> list[SkillGap]:
    return [
        SkillGap(
            skill=keyword,
            evidence="岗位描述强调了这项能力，但候选人资料里还没有明显证据。",
            recommendation=f"补充一个具体项目 bullet，说明你如何使用或体现了 {keyword}。",
        )
        for keyword in missing[:5]
    ]


def build_tailored_bullets(
    request: AnalyzeRequest,
    matched: list[str],
    missing: list[str],
    evidence_snippets: list[EvidenceSnippet] | None = None,
) -> list[ResumeBullet]:
    evidence_snippets = evidence_snippets or []
    llm_bullets = generate_grounded_bullets_with_llm(request, evidence_snippets)
    if llm_bullets:
        return llm_bullets

    bullets: list[ResumeBullet] = []

    for evidence in evidence_snippets[:3]:
        bullets.append(
            ResumeBullet(
                original_focus=evidence.snippet,
                rewritten_bullet=(
                    f"围绕 {evidence.keyword} 交付相关项目，基于已有经历「{evidence.snippet}」"
                    "提炼岗位匹配价值；投递前请补充真实量化结果。"
                ),
                evidence_keyword=evidence.keyword,
                evidence_source=evidence.source,
                evidence_snippet=evidence.snippet,
                grounded=True,
            )
        )

    if len(bullets) >= 3:
        return bullets

    used_keywords = {bullet.evidence_keyword for bullet in bullets if bullet.evidence_keyword}
    unsupported_keywords = [
        keyword for keyword in (missing + matched) if keyword not in used_keywords
    ]
    for keyword in unsupported_keywords[: 3 - len(bullets)]:
        bullets.append(
            ResumeBullet(
                original_focus=f"{keyword} 证据不足",
                rewritten_bullet=(
                    f"暂不建议直接声称你具备 {keyword} 经验；请先补充一个真实项目、职责或指标，"
                    "再生成可投递的简历 bullet。"
                ),
                evidence_keyword=keyword,
                grounded=False,
            )
        )

    return bullets


def build_interview_questions(
    request: AnalyzeRequest, matched: list[str], missing: list[str]
) -> list[str]:
    role = request.role_title or "目标岗位"
    questions = [
        f"请介绍一个最能证明你胜任 {role} 的项目。",
        "你如何衡量自己的技术方案是否真正帮助了用户或业务？",
    ]
    questions.extend(
        f"请具体讲讲你在 {keyword} 方面的实战经验。"
        for keyword in (matched + missing)[:6]
    )
    return questions[:8]


def build_summary(
    request: AnalyzeRequest, score: int, matched: list[str], missing: list[str]
) -> str:
    role = request.role_title or "目标岗位"
    company = f"（{request.company}）" if request.company else ""
    strongest = ", ".join(matched[:5]) or "通用项目经验"
    weakest = ", ".join(missing[:5]) or "岗位描述中未明显体现的能力"
    return (
        f"你的候选人资料与 {role}{company} 的初始匹配度为 {score}/100。"
        f"当前重合度最高的方向是：{strongest}；"
        f"最值得补强的方向是：{weakest}。"
    )


def build_next_actions() -> list[str]:
    return [
        "优先重写 3 条有证据支撑的简历 bullet，让表达更贴近岗位描述。",
        "对证据不足的关键词，先补充真实项目经历，再生成投递材料。",
        "补充可量化结果，例如延迟、收入、使用人数、成本或节省时间。",
        "所有生成内容在投递前都要人工确认，避免夸大或编造经历。",
    ]


def analyze_locally(request: AnalyzeRequest) -> AnalyzeResponse:
    resume_keywords = extract_resume_keywords(request)
    job_keywords = extract_job_keywords(request)
    matched, missing = compare_keywords(resume_keywords, job_keywords)
    score = calculate_score(matched, job_keywords)
    evidence_snippets = retrieve_resume_evidence(request, matched[:12])

    return AnalyzeResponse(
        match_score=score,
        summary=build_summary(request, score, matched, missing),
        matched_keywords=matched[:12],
        missing_keywords=missing,
        evidence_snippets=evidence_snippets,
        skill_gaps=build_skill_gaps(missing),
        tailored_bullets=build_tailored_bullets(
            request,
            matched[:5],
            missing[:3],
            evidence_snippets,
        ),
        interview_questions=build_interview_questions(request, matched[:4], missing[:4]),
        next_actions=build_next_actions(),
    )
