# Roadmap

## Phase 1: MVP

- FastAPI `/analyze` endpoint
- React workspace for resume and JD input
- Local deterministic fit scoring
- Skill gap and interview question generation

## Phase 2: Agent Workflow

- Convert the workflow into explicit LangGraph nodes
- Add state persistence for long-running application workflows
- Add human approval checkpoints before final application artifacts
- Add retries and structured error handling around model calls

## Phase 3: Retrieval

- Ingest resume versions, project notes, GitHub summaries, and company notes
- Use LlamaIndex for chunking, indexing, and retrieval
- Ground every generated bullet in retrieved evidence
- Add citation-style evidence snippets for recruiter-facing claims

## Phase 4: Production Features

- Postgres application tracker
- pgvector or managed vector store
- Auth and per-user workspaces
- Export tailored resumes and cover letters
- Tracing and evaluation dashboards

## Phase 5: Hiring Story

- Demo video
- Architecture diagram
- Before/after resume examples
- Evaluation report showing quality improvements over baseline prompts

