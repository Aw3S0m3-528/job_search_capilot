from __future__ import annotations

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextBlock:
    text: str
    x0: float
    top: float
    bottom: float
    page_number: int


def extract_layout_aware_pdf_text(content: bytes) -> str:
    try:
        import pdfplumber

        page_texts: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_index, page in enumerate(pdf.pages):
                words = page.extract_words(
                    keep_blank_chars=False,
                    use_text_flow=False,
                    extra_attrs=[],
                )
                blocks = words_to_blocks(words, page_index + 1)
                ordered = order_blocks_for_resume(blocks, page.width)
                page_text = "\n".join(block.text for block in ordered if block.text.strip())
                if page_text.strip():
                    page_texts.append(page_text)
        return "\n\n".join(page_texts)
    except Exception as exc:
        logger.warning("Layout-aware PDF extraction failed: %s", exc)
        return ""


def words_to_blocks(words: list[dict[str, object]], page_number: int) -> list[TextBlock]:
    if not words:
        return []

    sorted_words = sorted(words, key=lambda word: (float(word["top"]), float(word["x0"])))
    lines: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    current_top: float | None = None

    for word in sorted_words:
        top = float(word["top"])
        if current_top is None or abs(top - current_top) <= 3.0:
            current.append(word)
            current_top = top if current_top is None else current_top
        else:
            lines.append(current)
            current = [word]
            current_top = top
    if current:
        lines.append(current)

    blocks: list[TextBlock] = []
    for line in lines:
        ordered_line = sorted(line, key=lambda word: float(word["x0"]))
        text = " ".join(str(word["text"]) for word in ordered_line).strip()
        if not text:
            continue
        blocks.append(
            TextBlock(
                text=text,
                x0=min(float(word["x0"]) for word in ordered_line),
                top=min(float(word["top"]) for word in ordered_line),
                bottom=max(float(word["bottom"]) for word in ordered_line),
                page_number=page_number,
            )
        )
    return blocks


def order_blocks_for_resume(blocks: list[TextBlock], page_width: float) -> list[TextBlock]:
    if not blocks:
        return []

    left, right = split_columns(blocks, page_width)
    if not right:
        return sorted(blocks, key=lambda block: (block.page_number, block.top, block.x0))

    return sorted(left, key=lambda block: (block.page_number, block.top, block.x0)) + sorted(
        right, key=lambda block: (block.page_number, block.top, block.x0)
    )


def split_columns(blocks: list[TextBlock], page_width: float) -> tuple[list[TextBlock], list[TextBlock]]:
    midpoint = page_width / 2
    right = [block for block in blocks if block.x0 >= midpoint]
    left = [block for block in blocks if block.x0 < midpoint]

    if len(left) < 3 or len(right) < 3:
        return blocks, []

    right_ratio = len(right) / max(len(blocks), 1)
    if right_ratio < 0.2 or right_ratio > 0.8:
        return blocks, []

    return left, right

