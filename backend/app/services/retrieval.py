from __future__ import annotations

from dataclasses import dataclass

from app.models import AnalyzeRequest, EvidenceSnippet
from app.services.text import sentence_candidates, tokenize


@dataclass(frozen=True)
class EvidenceDocument:
    source: str
    text: str


def build_evidence_documents(request: AnalyzeRequest) -> list[EvidenceDocument]:
    documents = [EvidenceDocument(source="resume", text=request.resume_text)]
    if request.supplemental_materials.strip():
        documents.append(
            EvidenceDocument(
                source="supplemental_materials",
                text=request.supplemental_materials,
            )
        )
    return documents


def retrieve_resume_evidence(
    request: AnalyzeRequest, keywords: list[str], limit: int = 6
) -> list[EvidenceSnippet]:
    """Retrieve candidate evidence for matched JD keywords.

    This is a deterministic lexical retriever. It gives the project a grounded
    evidence layer now, while preserving the same service boundary where a
    LlamaIndex vector retriever can be plugged in later.
    """
    documents = build_evidence_documents(request)
    evidence: list[EvidenceSnippet] = []

    for keyword in keywords:
        keyword_tokens = set(tokenize(keyword))
        if not keyword_tokens:
            continue

        best_sentence = ""
        best_source = ""
        best_score = 0.0
        for document in documents:
            for sentence in sentence_candidates(document.text, limit=32):
                sentence_tokens = set(tokenize(sentence))
                overlap = keyword_tokens & sentence_tokens
                exact_bonus = 0.4 if keyword.lower() in sentence.lower() else 0.0
                source_bonus = 0.05 if document.source == "resume" else 0.0
                score = min(
                    1.0,
                    (len(overlap) / max(len(keyword_tokens), 1)) + exact_bonus + source_bonus,
                )
                if score > best_score:
                    best_sentence = sentence
                    best_source = document.source
                    best_score = score

        if best_sentence and best_score > 0:
            evidence.append(
                EvidenceSnippet(
                    keyword=keyword,
                    source=best_source,
                    snippet=best_sentence,
                    relevance_score=round(best_score, 2),
                )
            )

    return sorted(evidence, key=lambda item: item.relevance_score, reverse=True)[:limit]
