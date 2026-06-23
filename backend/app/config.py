from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(BACKEND_ROOT / ".env", override=True)
load_dotenv(PROJECT_ROOT / ".env", override=True)


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def llm_enabled() -> bool:
    provider = llm_provider()
    if provider == "openai":
        return get_bool_env("USE_LLM", default=False) and bool(os.getenv("OPENAI_API_KEY"))
    if provider == "deepseek":
        return get_bool_env("USE_LLM", default=False) and bool(os.getenv("DEEPSEEK_API_KEY"))
    return False


def llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").strip().lower()


def openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def deepseek_model() -> str:
    return os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")


def deepseek_base_url() -> str:
    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def active_model() -> str:
    if llm_provider() == "deepseek":
        return deepseek_model()
    return openai_model()


def ocr_space_api_key() -> str:
    return os.getenv("OCR_SPACE_API_KEY", "")


def ocr_space_endpoint() -> str:
    return os.getenv("OCR_SPACE_ENDPOINT", "https://api.ocr.space/parse/image")


def ocr_space_engine() -> str:
    return os.getenv("OCR_SPACE_ENGINE", "3")


def ocr_min_text_chars() -> int:
    return int(os.getenv("OCR_MIN_TEXT_CHARS", "300"))


def tavily_api_key() -> str:
    return os.getenv("TAVILY_API_KEY", "")


def tavily_endpoint() -> str:
    return os.getenv("TAVILY_ENDPOINT", "https://api.tavily.com/search")
