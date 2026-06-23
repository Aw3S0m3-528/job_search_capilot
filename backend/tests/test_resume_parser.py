from app.services import resume_parser
from app.services.resume_parser import parse_resume_file


def test_parse_text_resume_file() -> None:
    result = parse_resume_file("resume.txt", "Python 后端工程师\nFastAPI 项目经验".encode())

    assert result.method == "text_file"
    assert "FastAPI" in result.text
    assert result.needs_review is False


def test_pdf_falls_back_to_ocr_when_text_layer_is_short(monkeypatch) -> None:
    monkeypatch.setattr(resume_parser, "extract_layout_aware_pdf_text", lambda content: "")
    monkeypatch.setattr(resume_parser, "extract_pdf_text_layer", lambda content: "")
    monkeypatch.setattr(resume_parser, "extract_with_ocr_api", lambda filename, content: "OCR 简历文本")
    monkeypatch.setattr(resume_parser, "clean_resume_text", lambda text: f"cleaned:{text}")

    result = parse_resume_file("resume.pdf", b"%PDF fake")

    assert result.method in {"ocr_api", "ocr_api_llm_cleaned"}
    assert result.text == "cleaned:OCR 简历文本"
    assert result.needs_review is True
    assert result.warnings


def test_pdf_returns_warning_when_ocr_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(resume_parser, "extract_layout_aware_pdf_text", lambda content: "")
    monkeypatch.setattr(resume_parser, "extract_pdf_text_layer", lambda content: "")
    monkeypatch.setattr(resume_parser, "extract_with_ocr_api", lambda filename, content: "")

    result = parse_resume_file("resume.pdf", b"%PDF fake")

    assert result.method == "pdf_text_layer_insufficient"
    assert result.needs_review is True
    assert any("OCR" in warning for warning in result.warnings)


def test_pdf_uses_layout_text_before_basic_text_layer(monkeypatch) -> None:
    monkeypatch.setattr(
        resume_parser,
        "extract_layout_aware_pdf_text",
        lambda content: "基本信息\n技能\n项目经历\n" + ("FastAPI " * 80),
    )
    monkeypatch.setattr(resume_parser, "extract_pdf_text_layer", lambda content: "")

    result = parse_resume_file("resume.pdf", b"%PDF fake")

    assert result.method == "pdf_layout_text"
    assert "FastAPI" in result.text
    assert result.needs_review is False


def test_pdf_selects_basic_text_when_layout_has_cid_noise(monkeypatch) -> None:
    monkeypatch.setattr(
        resume_parser,
        "extract_layout_aware_pdf_text",
        lambda content: "项目经历 " + ("(cid:51) " * 30) + ("乱码 " * 80),
    )
    monkeypatch.setattr(
        resume_parser,
        "extract_pdf_text_layer",
        lambda content: "项目经历 MATLAB 仿真 教育经历 技能 Python " + ("完整文本 " * 80),
    )

    result = parse_resume_file("resume.pdf", b"%PDF fake")

    assert result.method == "pdf_text_layer"
    assert "MATLAB" in result.text
    assert result.warnings
