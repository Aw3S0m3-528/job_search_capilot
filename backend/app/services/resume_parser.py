from __future__ import annotations

import io
import logging
import re

import httpx
from pypdf import PdfReader

from app.config import (
    llm_enabled,
    ocr_min_text_chars,
    ocr_space_api_key,
    ocr_space_endpoint,
    ocr_space_engine,
)
from app.models import ParseResumeResponse
from app.services.llm import complete_text
from app.services.pdf_layout import extract_layout_aware_pdf_text

logger = logging.getLogger(__name__)

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md"}


def parse_resume_file(filename: str, content: bytes) -> ParseResumeResponse:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    extension = f".{suffix}" if suffix else ""

    if extension in SUPPORTED_TEXT_EXTENSIONS:
        raw_text = decode_text(content)
        cleaned = clean_resume_text(raw_text)
        return ParseResumeResponse(
            text=cleaned,
            method="text_file",
            needs_review=False,
            raw_text_length=len(raw_text),
        )

    if extension == ".pdf":
        return parse_pdf_resume(filename, content)

    return ParseResumeResponse(
        text="",
        method="unsupported",
        needs_review=True,
        warnings=["暂不支持该文件类型，请上传 txt、md 或 pdf。"],
    )


def parse_pdf_resume(filename: str, content: bytes) -> ParseResumeResponse:
    warnings: list[str] = []
    layout_text = extract_layout_aware_pdf_text(content)
    layout_normalized = normalize_text(layout_text)
    text_layer = extract_pdf_text_layer(content)
    normalized_text = normalize_text(text_layer)
    selected_text, selected_method = select_best_pdf_text(layout_normalized, normalized_text)

    if len(selected_text) >= ocr_min_text_chars():
        if selected_method == "pdf_text_layer" and layout_normalized:
            warnings.append("版面感知提取存在缺字或编码噪声，已选择基础文本层结果。")
        cleaned = clean_resume_text(selected_text)
        return ParseResumeResponse(
            text=cleaned,
            method=selected_method,
            needs_review=False,
            warnings=warnings,
            raw_text_length=len(selected_text),
        )

    if layout_normalized or normalized_text:
        warnings.append("PDF 文本层内容较少，已按扫描 PDF 尝试 OCR。")

    ocr_text = extract_with_ocr_api(filename, content)
    if ocr_text:
        cleaned = clean_resume_text(ocr_text)
        return ParseResumeResponse(
            text=cleaned,
            method="ocr_api_llm_cleaned" if llm_enabled() else "ocr_api",
            needs_review=True,
            warnings=warnings + ["OCR 结果可能存在识别误差，请在投递前人工检查。"],
            raw_text_length=len(ocr_text),
        )

    fallback = selected_text
    warnings.append("OCR 未启用或未成功，请上传可选中文本 PDF，或手动复制粘贴简历。")
    return ParseResumeResponse(
        text=fallback,
        method="pdf_text_layer_insufficient",
        needs_review=True,
        warnings=warnings,
        raw_text_length=len(fallback),
    )


def select_best_pdf_text(layout_text: str, basic_text: str) -> tuple[str, str]:
    if layout_text_is_usable(layout_text, basic_text):
        return layout_text, "pdf_layout_text"
    layout_score = pdf_text_quality_score(layout_text)
    basic_score = pdf_text_quality_score(basic_text)
    if layout_score >= basic_score:
        return layout_text, "pdf_layout_text"
    return basic_text, "pdf_text_layer"


def layout_text_is_usable(layout_text: str, basic_text: str) -> bool:
    if len(layout_text) < 200:
        return False
    if basic_text and len(layout_text) < len(basic_text) * 0.55:
        return False
    cid_count = layout_text.count("(cid:")
    max_cid_noise = max(4, len(layout_text) // 180)
    return cid_count <= max_cid_noise


def pdf_text_quality_score(text: str) -> float:
    if not text:
        return 0
    cid_penalty = text.count("(cid:") * 180
    replacement_penalty = text.count("\ufffd") * 80
    mojibake_penalty = mojibake_score(text) * 35
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_word_count = len(re.findall(r"[A-Za-z]{2,}", text))
    section_bonus = sum(
        60
        for section in ("教育", "项目", "经历", "技能", "荣誉", "评价")
        if section in text
    )
    return (
        len(text)
        + cjk_count * 0.2
        + ascii_word_count * 3
        + section_bonus
        - cid_penalty
        - replacement_penalty
        - mojibake_penalty
    )


def mojibake_score(text: str) -> int:
    markers = (
        "å",
        "æ",
        "è",
        "ç",
        "ï¼",
        "ã€",
        "â€",
        "é¡",
        "ç›",
        "èƒ",
    )
    return sum(text.count(marker) for marker in markers)


def decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def extract_pdf_text_layer(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        page_text = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(page_text)
    except Exception as exc:
        logger.warning("PDF text layer extraction failed: %s", exc)
        return ""


def extract_with_ocr_api(filename: str, content: bytes) -> str:
    api_key = ocr_space_api_key()
    if not api_key:
        return ""

    try:
        response = httpx.post(
            ocr_space_endpoint(),
            headers={"apikey": api_key},
            data={
                "language": "auto",
                "OCREngine": ocr_space_engine(),
                "scale": "true",
                "isTable": "true",
                "detectOrientation": "true",
                "filetype": "PDF",
            },
            files={"file": (filename, content, "application/pdf")},
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("IsErroredOnProcessing"):
            logger.warning("OCR API failed: %s", payload.get("ErrorMessage"))
            return ""
        parsed_results = payload.get("ParsedResults") or []
        return normalize_text("\n".join(item.get("ParsedText") or "" for item in parsed_results))
    except Exception as exc:
        logger.warning("OCR API request failed: %s", exc)
        return ""


def clean_resume_text(raw_text: str) -> str:
    text = normalize_text(raw_text)
    if not text or not llm_enabled():
        return text

    prompt = (
        "请把下面 OCR 或 PDF 提取出的简历内容清洗成适合求职 Agent 分析的纯文本。"
        "要求：保留真实信息，不要编造；修复明显断行和多余空格；按模块组织为："
        "基本信息、求职方向、技能、工作经历、项目经历、教育经历、其他。"
        "如果某模块没有内容，可以省略。只输出清洗后的纯文本，不要 Markdown 代码块。\n\n"
        f"{text}"
    )
    cleaned = complete_text(prompt)
    return normalize_text(cleaned or text)


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
