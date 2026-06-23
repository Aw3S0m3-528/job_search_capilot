from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import active_model, llm_enabled, llm_provider
from app.models import AnalyzeRequest, AnalyzeResponse, ParseResumeResponse
from app.models import JobResearchRequest, JobResearchResponse
from app.services.job_research import research_job
from app.services.resume_parser import parse_resume_file
from app.workflow import run_job_match_workflow

app = FastAPI(
    title="Job Search Copilot API",
    description="Agentic resume and job-description analysis for targeted applications.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict[str, str | bool]:
    return {
        "llm_enabled": llm_enabled(),
        "llm_provider": llm_provider(),
        "active_model": active_model(),
        "bullet_generation": f"{llm_provider()}_api" if llm_enabled() else "local_grounded_templates",
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_job_fit(request: AnalyzeRequest) -> AnalyzeResponse:
    return run_job_match_workflow(request)


@app.post("/parse-resume", response_model=ParseResumeResponse)
async def parse_resume(file: UploadFile = File(...)) -> ParseResumeResponse:
    content = await file.read()
    return parse_resume_file(file.filename or "resume", content)


@app.post("/research-job", response_model=JobResearchResponse)
def research_target_job(request: JobResearchRequest) -> JobResearchResponse:
    return research_job(request)
