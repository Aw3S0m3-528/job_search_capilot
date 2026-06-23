from __future__ import annotations

import json
import logging
import os

from app.config import deepseek_base_url, deepseek_model, llm_enabled, llm_provider, openai_model
from app.models import AnalyzeRequest, EvidenceSnippet, ResumeBullet

logger = logging.getLogger(__name__)


def generate_grounded_bullets_with_llm(
    request: AnalyzeRequest,
    evidence_snippets: list[EvidenceSnippet],
    limit: int = 3,
) -> list[ResumeBullet] | None:
    if not llm_enabled() or not evidence_snippets:
        return None

    try:
        prompt = build_bullet_prompt(request, evidence_snippets[:limit], limit)
        if llm_provider() == "deepseek":
            raw_text = call_deepseek(prompt)
        else:
            raw_text = call_openai(prompt)
        return parse_bullets(raw_text, limit)
    except Exception as exc:
        logger.warning("LLM bullet generation failed; falling back to local generator: %s", exc)
        return None


def complete_text(prompt: str) -> str | None:
    if not llm_enabled():
        return None

    try:
        if llm_provider() == "deepseek":
            return call_deepseek(prompt)
        return call_openai(prompt)
    except Exception as exc:
        logger.warning("LLM text completion failed: %s", exc)
        return None


def call_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(model=openai_model(), input=prompt)
    return response.output_text


def call_deepseek(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=deepseek_base_url(),
    )
    response = client.chat.completions.create(
        model=deepseek_model(),
        messages=[
            {
                "role": "system",
                "content": "你是一个谨慎的求职简历改写助手，只输出合法 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content or ""


def parse_bullets(raw_text: str, limit: int) -> list[ResumeBullet] | None:
    payload = json.loads(strip_json_code_fence(raw_text))
    bullets = [
        ResumeBullet(
            original_focus=item["evidence_snippet"],
            rewritten_bullet=item["rewritten_bullet"],
            evidence_keyword=item["evidence_keyword"],
            evidence_source=item["evidence_source"],
            evidence_snippet=item["evidence_snippet"],
            grounded=True,
        )
        for item in payload.get("bullets", [])[:limit]
        if item.get("rewritten_bullet") and item.get("evidence_snippet")
    ]
    return bullets or None


def strip_json_code_fence(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        text = text.removesuffix("```").strip()
    return text


def build_bullet_prompt(
    request: AnalyzeRequest, evidence_snippets: list[EvidenceSnippet], limit: int
) -> str:
    evidence_payload = [
        {
            "keyword": item.keyword,
            "source": item.source,
            "snippet": item.snippet,
            "relevance_score": item.relevance_score,
        }
        for item in evidence_snippets
    ]
    return (
        "你是一个谨慎的求职简历改写助手。只允许基于给定 evidence 改写简历 bullet，"
        "不能编造公司、学历、指标、技能或未出现的经历。"
        "如果 evidence 没有量化指标，只能提示用户补充真实指标。\n\n"
        f"目标公司：{request.company or '未提供'}\n"
        f"目标岗位：{request.role_title or '未提供'}\n"
        f"岗位描述：{request.job_description}\n\n"
        f"请输出 JSON，不要输出 Markdown。JSON 格式："
        '{"bullets":[{"evidence_keyword":"...","evidence_source":"resume|supplemental_materials",'
        '"evidence_snippet":"...","rewritten_bullet":"..."}]}\n'
        f"最多输出 {limit} 条。每条 rewritten_bullet 必须是中文，且必须能从 evidence_snippet 直接推出。\n\n"
        f"Evidence:\n{json.dumps(evidence_payload, ensure_ascii=False)}"
    )
