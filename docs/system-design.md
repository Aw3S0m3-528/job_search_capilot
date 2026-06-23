# System Design Notes

## Core Entities

- Candidate profile: resume text, project history, skills, links
- Job target: company, role, job description, source URL, status
- Fit report: score, matched evidence, gaps, drafts, interview plan
- Application artifact: resume version, cover letter, outreach message

## Agent Responsibilities

- Extractor Agent: normalize resume and JD into structured requirements
- Retriever Agent: find candidate evidence relevant to each requirement
- Scoring Agent: produce fit score and explain missing evidence
- Drafting Agent: write targeted bullets and interview stories
- Reviewer Agent: check claims for unsupported or exaggerated statements

## Guardrails

- Do not submit applications automatically.
- Do not invent employers, metrics, degrees, or skills.
- Mark generated bullets as drafts until the user approves them.
- Prefer "needs evidence" over confident unsupported claims.

