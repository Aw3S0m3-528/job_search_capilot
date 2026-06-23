from app.services.pdf_layout import TextBlock, order_blocks_for_resume, split_columns


def test_order_blocks_for_two_column_resume_reads_left_then_right() -> None:
    blocks = [
        TextBlock("右栏 技能", x0=330, top=10, bottom=20, page_number=1),
        TextBlock("左栏 基本信息", x0=40, top=10, bottom=20, page_number=1),
        TextBlock("右栏 教育经历", x0=330, top=40, bottom=50, page_number=1),
        TextBlock("左栏 工作经历", x0=40, top=40, bottom=50, page_number=1),
        TextBlock("右栏 项目经历", x0=330, top=70, bottom=80, page_number=1),
        TextBlock("左栏 联系方式", x0=40, top=70, bottom=80, page_number=1),
    ]

    ordered = order_blocks_for_resume(blocks, page_width=600)

    assert [block.text for block in ordered] == [
        "左栏 基本信息",
        "左栏 工作经历",
        "左栏 联系方式",
        "右栏 技能",
        "右栏 教育经历",
        "右栏 项目经历",
    ]


def test_split_columns_ignores_single_column_layout() -> None:
    blocks = [
        TextBlock("基本信息", x0=40, top=10, bottom=20, page_number=1),
        TextBlock("技能", x0=42, top=40, bottom=50, page_number=1),
        TextBlock("项目经历", x0=41, top=70, bottom=80, page_number=1),
    ]

    left, right = split_columns(blocks, page_width=600)

    assert left == blocks
    assert right == []

