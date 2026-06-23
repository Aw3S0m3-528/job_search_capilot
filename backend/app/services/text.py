from __future__ import annotations

import re
from collections import Counter

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "you",
    "your",
}

TECH_ALIASES = {
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "azure": "Azure",
    "docker": "Docker",
    "fastapi": "FastAPI",
    "gcp": "GCP",
    "github": "GitHub",
    "javascript": "JavaScript",
    "kubernetes": "Kubernetes",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "llamaindex": "LlamaIndex",
    "mcp": "MCP",
    "nextjs": "Next.js",
    "node": "Node.js",
    "postgres": "Postgres",
    "python": "Python",
    "rag": "RAG",
    "react": "React",
    "typescript": "TypeScript",
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{1,}", text.lower())


def extract_keywords(text: str, limit: int = 24) -> list[str]:
    tokens = [
        normalize_token(token)
        for token in tokenize(text)
        if token not in STOPWORDS and len(token) > 2
    ]
    counts = Counter(tokens)
    return [keyword for keyword, _ in counts.most_common(limit)]


def normalize_token(token: str) -> str:
    compact = token.replace(".", "").replace("-", "")
    return TECH_ALIASES.get(compact, TECH_ALIASES.get(token, token))


def sentence_candidates(text: str, limit: int = 6) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    cleaned = [sentence.strip(" -\t") for sentence in sentences if len(sentence.strip()) > 30]
    return cleaned[:limit]

