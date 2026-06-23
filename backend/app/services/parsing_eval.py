from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResumeEvalSpec:
    sample_id: str
    expected_text: str
    parsed_text: str
    required_keywords: list[str]
    required_sections: list[str]


def normalize_for_eval(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def compact_for_eval(text: str) -> str:
    return re.sub(r"\s+", "", text).strip().lower()


def keyword_recall(parsed_text: str, required_keywords: list[str]) -> float:
    if not required_keywords:
        return 1.0
    parsed = normalize_for_eval(parsed_text)
    hits = sum(1 for keyword in required_keywords if keyword.lower() in parsed)
    return hits / len(required_keywords)


def section_recall(parsed_text: str, required_sections: list[str]) -> float:
    if not required_sections:
        return 1.0
    parsed = normalize_for_eval(parsed_text)
    hits = sum(1 for section in required_sections if section.lower() in parsed)
    return hits / len(required_sections)


def char_recall(parsed_text: str, expected_text: str) -> float:
    expected = normalize_for_eval(expected_text)
    parsed = normalize_for_eval(parsed_text)
    if not expected:
        return 1.0

    if contains_cjk(expected):
        expected_units = cjk_ngrams(compact_for_eval(expected_text))
        parsed_compact = compact_for_eval(parsed_text)
        if not expected_units:
            return min(1.0, len(parsed_compact) / max(len(compact_for_eval(expected_text)), 1))
        hits = sum(1 for unit in expected_units if unit in parsed_compact)
        return hits / len(expected_units)

    expected_tokens = expected.split()
    if len(expected_tokens) <= 1:
        return min(1.0, len(parsed) / max(len(expected), 1))

    hits = sum(1 for token in expected_tokens if token in parsed)
    return hits / len(expected_tokens)


def truncation_risk(parsed_text: str, expected_text: str) -> bool:
    parsed = normalize_for_eval(parsed_text)
    expected = normalize_for_eval(expected_text)
    if not expected:
        return False
    if len(parsed) < len(expected) * 0.65:
        return True

    if contains_cjk(expected):
        expected_compact = compact_for_eval(expected_text)
        parsed_compact = compact_for_eval(parsed_text)
        expected_tail = expected_compact[-max(80, min(240, len(expected_compact) // 4)) :]
        tail_units = cjk_ngrams(expected_tail)
        if not tail_units:
            return False
        hits = sum(1 for unit in tail_units if unit in parsed_compact)
        return hits / len(tail_units) < 0.45

    expected_tail = expected[-max(80, min(240, len(expected) // 4)) :]
    tail_tokens = [token for token in expected_tail.split() if len(token) > 2]
    if not tail_tokens:
        return False
    hits = sum(1 for token in tail_tokens if token in parsed)
    return hits / len(tail_tokens) < 0.35


def evaluate_resume_parse(spec: ResumeEvalSpec) -> dict[str, object]:
    char = char_recall(spec.parsed_text, spec.expected_text)
    keywords = keyword_recall(spec.parsed_text, spec.required_keywords)
    sections = section_recall(spec.parsed_text, spec.required_sections)
    truncated = truncation_risk(spec.parsed_text, spec.expected_text)
    return {
        "sample_id": spec.sample_id,
        "char_recall": round(char, 4),
        "keyword_recall": round(keywords, 4),
        "section_recall": round(sections, 4),
        "truncated": truncated,
        "parsed_chars": len(spec.parsed_text),
        "expected_chars": len(spec.expected_text),
    }


def diagnose_resume_parse(spec: ResumeEvalSpec) -> dict[str, object]:
    parsed = normalize_for_eval(spec.parsed_text)
    expected = normalize_for_eval(spec.expected_text)
    if contains_cjk(expected):
        parsed_for_tail = compact_for_eval(spec.parsed_text)
        expected_compact = compact_for_eval(spec.expected_text)
        expected_tail = expected_compact[-max(80, min(240, len(expected_compact) // 4)) :]
        tail_tokens = cjk_ngrams(expected_tail)
        missing_tail_tokens = [token for token in tail_tokens if token not in parsed_for_tail]
    else:
        expected_tail = expected[-max(80, min(240, len(expected) // 4)) :]
        tail_tokens = unique_tokens(expected_tail)
        missing_tail_tokens = [token for token in tail_tokens if token not in parsed]
    return {
        "sample_id": spec.sample_id,
        "missing_keywords": [
            keyword for keyword in spec.required_keywords if keyword.lower() not in parsed
        ],
        "missing_sections": [
            section for section in spec.required_sections if section.lower() not in parsed
        ],
        "missing_tail_tokens": missing_tail_tokens[:40],
        "expected_tail": spec.expected_text[-500:],
        "parsed_tail": spec.parsed_text[-500:],
    }


def unique_tokens(text: str) -> list[str]:
    tokens = [token for token in re.split(r"\s+", text) if len(token) > 2]
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def cjk_ngrams(text: str, size: int = 4) -> list[str]:
    clean = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    if len(clean) <= size:
        return [clean] if clean else []
    grams = [clean[index : index + size] for index in range(0, len(clean) - size + 1)]
    seen: set[str] = set()
    unique: list[str] = []
    for gram in grams:
        if gram not in seen:
            seen.add(gram)
            unique.append(gram)
    return unique


def load_eval_spec(sample_dir: Path) -> ResumeEvalSpec:
    metadata_path = sample_dir / "metadata.json"
    expected_path = sample_dir / "expected.txt"
    parsed_path = sample_dir / "parsed.txt"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    return ResumeEvalSpec(
        sample_id=sample_dir.name,
        expected_text=expected_path.read_text(encoding="utf-8"),
        parsed_text=parsed_path.read_text(encoding="utf-8"),
        required_keywords=metadata.get("required_keywords", []),
        required_sections=metadata.get("required_sections", []),
    )
