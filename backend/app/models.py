from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    resume_text: str = Field(min_length=20)
    job_description: str = Field(min_length=20)
    company: str | None = None
    role_title: str | None = None
    supplemental_materials: str = ""


class SkillGap(BaseModel):
    skill: str
    evidence: str
    recommendation: str


class ResumeBullet(BaseModel):
    original_focus: str
    rewritten_bullet: str
    evidence_keyword: str | None = None
    evidence_source: str | None = None
    evidence_snippet: str | None = None
    grounded: bool = False


class EvidenceSnippet(BaseModel):
    keyword: str
    source: str
    snippet: str
    relevance_score: float = Field(ge=0, le=1)


class AnalyzeResponse(BaseModel):
    match_score: int = Field(ge=0, le=100)
    summary: str
    matched_keywords: list[str]
    missing_keywords: list[str]
    evidence_snippets: list[EvidenceSnippet]
    skill_gaps: list[SkillGap]
    tailored_bullets: list[ResumeBullet]
    interview_questions: list[str]
    next_actions: list[str]


class ParseResumeResponse(BaseModel):
    text: str
    method: str
    needs_review: bool = False
    warnings: list[str] = []
    raw_text_length: int = 0


class JobResearchRequest(BaseModel):
    company: str = ""
    role_title: str = ""
    job_description: str = Field(min_length=20)
    resume_text: str = ""
    supplemental_materials: str = ""


class ResearchSource(BaseModel):
    title: str
    url: str
    content: str
    score: float = 0


class JobResearchResponse(BaseModel):
    research_summary: str
    company_signals: list[str]
    role_signals: list[str]
    resume_positioning_advice: list[str]
    interview_strategy: list[str]
    resume_rewrite_suggestions: list[str] = []
    cover_letter_draft: str = ""
    sources: list[ResearchSource]
    used_search: bool
    llm_validation_status: str = "not_used"
    llm_json_repaired: bool = False
    warnings: list[str] = []
