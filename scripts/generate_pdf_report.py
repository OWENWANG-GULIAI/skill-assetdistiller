#!/usr/bin/env python3
"""Generate a GULIAI-branded experience-asset commercialization PDF."""

import argparse
import html
import json
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
USER_FONT_DIR = Path.home() / "Library" / "Fonts"
PALETTE = {
    "gold": colors.HexColor("#D89808"),
    "deep_gold": colors.HexColor("#A96F00"),
    "pale_gold": colors.HexColor("#F4E7C5"),
    "soft_gold": colors.HexColor("#FBF7EC"),
    "charcoal": colors.HexColor("#181818"),
    "gray": colors.HexColor("#6E6E6E"),
    "warm_gray": colors.HexColor("#D9D4C8"),
    "light_gray": colors.HexColor("#F3F1EC"),
    "paper": colors.HexColor("#FFFFFF"),
}
TABLE_HEADER_BACKGROUND = PALETTE["pale_gold"]

FONT_REGULAR = "GuliaiSans"
FONT_MEDIUM = "GuliaiSansMedium"
FONT_BOLD = "GuliaiSansBold"

FONT_CANDIDATES = {
    FONT_REGULAR: [
        ROOT / "assets" / "HarmonyOS_Sans_SC_Regular.ttf",
        USER_FONT_DIR / "HarmonyOS_Sans_SC_Regular.ttf",
    ],
    FONT_MEDIUM: [
        ROOT / "assets" / "HarmonyOS_Sans_SC_Medium.ttf",
        USER_FONT_DIR / "HarmonyOS_Sans_SC_Medium.ttf",
        ROOT / "assets" / "HarmonyOS_Sans_SC_Regular.ttf",
        USER_FONT_DIR / "HarmonyOS_Sans_SC_Regular.ttf",
    ],
    FONT_BOLD: [
        ROOT / "assets" / "HarmonyOS_Sans_SC_Bold.ttf",
        USER_FONT_DIR / "HarmonyOS_Sans_SC_Bold.ttf",
        ROOT / "assets" / "HarmonyOS_Sans_SC_Regular.ttf",
        USER_FONT_DIR / "HarmonyOS_Sans_SC_Regular.ttf",
    ],
}


def register_fonts():
    for name, candidates in FONT_CANDIDATES.items():
        for candidate in candidates:
            if candidate.exists():
                pdfmetrics.registerFont(TTFont(name, str(candidate)))
                break
        else:
            raise RuntimeError(
                f"找不到可嵌入的 HarmonyOS Sans SC 字体: {name}。"
                "请安装官方原始字体，或将未修改的字体文件放入 assets/；参见 assets/FONT-NOTICE.md。"
            )
    pdfmetrics.registerFontFamily(
        "GuliaiSansFamily",
        normal=FONT_REGULAR,
        bold=FONT_BOLD,
        italic=FONT_REGULAR,
        boldItalic=FONT_BOLD,
    )


register_fonts()


def esc(value):
    return html.escape(str(value if value is not None else ""))


def p(value, style):
    return Paragraph(esc(value).replace("\n", "<br/>"), style)


def rich(value, style):
    return Paragraph(str(value if value is not None else "").replace("\n", "<br/>"), style)


def bullets(items):
    return "<br/>".join(f"• {esc(item)}" for item in items)


def required(mapping, key, path):
    if not isinstance(mapping, dict) or key not in mapping or mapping[key] in (None, "", []):
        raise ValueError(f"报告数据缺少必填字段: {path}.{key}")


def asset_score(breakdown):
    values = [breakdown.get(key) for key in ("problem_value", "result_evidence", "moat", "portability", "product_readiness")]
    return None if any(value is None for value in values) else sum(values)


def product_score(breakdown):
    return sum(breakdown.get(key, 0) for key in ("customer_urgency", "experience_fit", "delivery_control", "buyer_clarity", "low_cost_validation"))


def requires_interview(experience):
    keys = ("scene", "challenge", "personal_role", "key_decision", "actions", "deliverables", "result_evidence", "transferable_method")
    missing = sum(1 for key in keys if not experience.get(key))
    return missing >= 3 or not experience.get("key_decision") or not experience.get("result_evidence")


def validate_report_data(data):
    top_level = (
        "mode", "meta", "executive_summary", "top_assets", "moat_analysis",
        "customer_segments", "monetization_offers", "primary_offer",
        "expert_interview", "roadmap", "evidence_ledger",
    )
    for key in top_level:
        required(data, key, "report")
    if data["mode"] not in {"preliminary", "interview_enriched", "evidence_verified"}:
        raise ValueError("report.mode 无效")
    for key in ("name", "date", "report_id", "keywords"):
        required(data["meta"], key, "meta")
    if len(data["top_assets"]) != 3:
        raise ValueError("top_assets 必须且只能包含 3 项")
    if not 2 <= len(data["customer_segments"]) <= 4:
        raise ValueError("customer_segments 必须包含 2-4 项")
    if not 3 <= len(data["monetization_offers"]) <= 5:
        raise ValueError("monetization_offers 必须包含 3-5 项")
    if len(data["roadmap"]) != 3:
        raise ValueError("roadmap 必须包含短期、中期、长期三个阶段")
    questions = data["expert_interview"].get("questions", [])
    if not 2 <= len(questions) <= 3:
        raise ValueError("expert_interview.questions 必须包含 2-3 项")

    asset_keys = (
        "rank", "name", "source_experience", "scene", "challenge", "personal_role",
        "high_value_problem", "key_decision", "counterintuitive_insight", "solution_mechanism",
        "deliverables", "result_evidence", "portability", "moat", "score_breakdown",
        "score_total", "maturity", "can_sell", "cannot_promise", "evidence_gap", "evidence_links",
    )
    for index, asset in enumerate(data["top_assets"]):
        for key in asset_keys:
            required(asset, key, f"top_assets[{index}]")
        expected = asset_score(asset["score_breakdown"])
        if expected != asset["score_total"]:
            raise ValueError(f"top_assets[{index}].score_total 应为 {expected}")
    if sorted(asset["rank"] for asset in data["top_assets"]) != [1, 2, 3]:
        raise ValueError("top_assets.rank 必须是 1、2、3")

    offer_keys = (
        "rank", "name", "category", "audience", "trigger", "paid_problem", "cost_of_inaction",
        "mechanism", "ai_role", "deliverables", "scope_excluded", "price_test", "pricing_basis",
        "high_ticket_condition", "score_breakdown", "score_total", "priority", "feasibility",
        "evidence_links", "validation_action", "recommendation",
    )
    for index, offer in enumerate(data["monetization_offers"]):
        for key in offer_keys:
            required(offer, key, f"monetization_offers[{index}]")
        expected = product_score(offer["score_breakdown"])
        if expected != offer["score_total"]:
            raise ValueError(f"monetization_offers[{index}].score_total 应为 {expected}")
        calculated = "P1" if expected >= 80 else ("P2" if expected >= 65 else "P3")
        if offer["priority"] != calculated:
            raise ValueError(f"monetization_offers[{index}].priority 应为 {calculated}")
    return True


def make_styles():
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle("eyebrow", parent=base["Normal"], fontName=FONT_MEDIUM, fontSize=9, leading=13.5, textColor=PALETTE["deep_gold"], tracking=0.5),
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontName=FONT_BOLD, fontSize=32, leading=48, textColor=PALETTE["charcoal"]),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=14, leading=21, textColor=PALETTE["gray"]),
        "cover_meta": ParagraphStyle("cover_meta", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=10.5, leading=15.75, textColor=PALETTE["charcoal"]),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=22, leading=33, textColor=PALETTE["charcoal"], spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT_MEDIUM, fontSize=15, leading=22.5, textColor=PALETTE["charcoal"], spaceBefore=6, spaceAfter=5),
        "focus": ParagraphStyle("focus", parent=base["BodyText"], fontName=FONT_MEDIUM, fontSize=13, leading=19.5, textColor=PALETTE["charcoal"]),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT_REGULAR, fontSize=10.5, leading=15.75, textColor=PALETTE["charcoal"], spaceAfter=5),
        "body_bold": ParagraphStyle("body_bold", parent=base["BodyText"], fontName=FONT_MEDIUM, fontSize=10.5, leading=15.75, textColor=PALETTE["charcoal"], spaceAfter=4),
        "muted": ParagraphStyle("muted", parent=base["BodyText"], fontName=FONT_REGULAR, fontSize=9.5, leading=14.25, textColor=PALETTE["gray"], spaceAfter=4),
        "table": ParagraphStyle("table", parent=base["BodyText"], fontName=FONT_REGULAR, fontSize=9.5, leading=14.25, textColor=PALETTE["charcoal"]),
        "table_head": ParagraphStyle("table_head", parent=base["BodyText"], fontName=FONT_MEDIUM, fontSize=9.5, leading=14.25, textColor=PALETTE["charcoal"], alignment=TA_CENTER),
        "metric": ParagraphStyle("metric", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=18, leading=27, textColor=PALETTE["gold"], alignment=TA_CENTER),
        "metric_label": ParagraphStyle("metric_label", parent=base["BodyText"], fontName=FONT_REGULAR, fontSize=9.5, leading=14.25, textColor=PALETTE["gray"], alignment=TA_CENTER),
        "right": ParagraphStyle("right", parent=base["BodyText"], fontName=FONT_REGULAR, fontSize=9.5, leading=14.25, textColor=PALETTE["gray"], alignment=TA_RIGHT),
    }


def brand_table(rows, widths, styles, repeat_rows=1, compact=False):
    rendered = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if row_index < repeat_rows else styles["table"]
        rendered.append([cell if isinstance(cell, (Paragraph, Drawing, Table)) else rich(cell, style) for cell in row])
    table = Table(rendered, colWidths=widths, repeatRows=repeat_rows, hAlign="LEFT", splitByRow=1)
    padding = 5 if compact else 7
    commands = [
        ("TEXTCOLOR", (0, 0), (-1, -1), PALETTE["charcoal"]),
        ("GRID", (0, 0), (-1, -1), 0.45, PALETTE["warm_gray"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    if repeat_rows:
        commands.insert(0, ("BACKGROUND", (0, 0), (-1, repeat_rows - 1), TABLE_HEADER_BACKGROUND))
    for row in range(repeat_rows, len(rows)):
        if (row - repeat_rows) % 2:
            commands.append(("BACKGROUND", (0, row), (-1, row), PALETTE["soft_gold"]))
    table.setStyle(TableStyle(commands))
    return table


def paired_table(rows, widths, styles, compact=False):
    """Render alternating label/value rows without repeating a false header across pages."""
    rendered = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if row_index % 2 == 0 else styles["table"]
        rendered.append([cell if isinstance(cell, (Paragraph, Drawing, Table)) else rich(cell, style) for cell in row])
    table = Table(rendered, colWidths=widths, repeatRows=0, hAlign="LEFT", splitByRow=1)
    padding = 4 if compact else 6
    commands = [
        ("TEXTCOLOR", (0, 0), (-1, -1), PALETTE["charcoal"]),
        ("GRID", (0, 0), (-1, -1), 0.45, PALETTE["warm_gray"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]
    for row_index in range(0, len(rows), 2):
        commands.append(("BACKGROUND", (0, row_index), (-1, row_index), TABLE_HEADER_BACKGROUND))
    table.setStyle(TableStyle(commands))
    return table


def focus_card(label, text, styles):
    table = Table([
        [p(label, styles["body_bold"]), p(text, styles["focus"])]
    ], colWidths=[34 * mm, 126 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["soft_gold"]),
        ("BACKGROUND", (0, 0), (0, 0), PALETTE["pale_gold"]),
        ("LINEBEFORE", (0, 0), (0, 0), 3, PALETTE["gold"]),
        ("BOX", (0, 0), (-1, -1), 0.45, PALETTE["warm_gray"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def subheading(code, title, styles):
    table = Table([[p(code, styles["h2"]), p(title, styles["h2"])]], colWidths=[23 * mm, 137 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, 0), 3, PALETTE["gold"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return table


def section_header(story, number, title, conclusion, styles):
    story.extend([
        p(f"GULIAI EXPERIENCE ASSET | {number:02d}", styles["eyebrow"]),
        Spacer(1, 2 * mm),
        p(f"{number}. {title}", styles["h1"]),
        HRFlowable(width="100%", thickness=1.1, color=PALETTE["gold"], spaceAfter=3 * mm),
        focus_card("本章结论", conclusion, styles),
        Spacer(1, 5 * mm),
    ])


def metric_cards(cards, styles):
    cells = []
    for value, label in cards:
        cells.append(Table([[p(value, styles["metric"])], [p(label, styles["metric_label"])]], colWidths=[50 * mm]))
    table = Table([cells], colWidths=[53.3 * mm] * len(cells), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["soft_gold"]),
        ("BOX", (0, 0), (-1, -1), 0.45, PALETTE["warm_gray"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, PALETTE["warm_gray"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def ranking_chart(assets):
    width, height = 160 * mm, 52 * mm
    drawing = Drawing(width, height)
    shades = [PALETTE["gold"], colors.HexColor("#E4B341"), colors.HexColor("#EDD18A")]
    drawing.add(String(0, height - 12, "Top 3 经验资产价值指数", fontName=FONT_MEDIUM, fontSize=11, fillColor=PALETTE["charcoal"]))
    for index, asset in enumerate(assets):
        y = height - 43 - index * 38
        drawing.add(String(0, y + 9, f"{asset['rank']}. {asset['name']}", fontName=FONT_REGULAR, fontSize=8.8, fillColor=PALETTE["charcoal"]))
        bar_x = 190
        drawing.add(Rect(bar_x, y, 235, 13, fillColor=PALETTE["light_gray"], strokeColor=None))
        drawing.add(Rect(bar_x, y, 235 * asset["score_total"] / 100, 13, fillColor=shades[index], strokeColor=None))
        drawing.add(String(432, y + 2, str(asset["score_total"]), fontName=FONT_BOLD, fontSize=9, fillColor=PALETTE["deep_gold"]))
    return drawing


def matrix_chart(items, x_getter, y_getter, label_getter, x_label, y_label, title):
    width, height = 160 * mm, 74 * mm
    drawing = Drawing(width, height)
    left, bottom, grid_w, grid_h = 52, 35, 360, 160
    drawing.add(String(0, height - 12, title, fontName=FONT_MEDIUM, fontSize=11, fillColor=PALETTE["charcoal"]))
    drawing.add(Rect(left, bottom, grid_w / 2, grid_h / 2, fillColor=PALETTE["light_gray"], strokeColor=None))
    drawing.add(Rect(left + grid_w / 2, bottom, grid_w / 2, grid_h / 2, fillColor=PALETTE["soft_gold"], strokeColor=None))
    drawing.add(Rect(left, bottom + grid_h / 2, grid_w / 2, grid_h / 2, fillColor=colors.HexColor("#F8F1DF"), strokeColor=None))
    drawing.add(Rect(left + grid_w / 2, bottom + grid_h / 2, grid_w / 2, grid_h / 2, fillColor=PALETTE["pale_gold"], strokeColor=None))
    drawing.add(Line(left, bottom, left + grid_w, bottom, strokeColor=PALETTE["gray"], strokeWidth=0.7))
    drawing.add(Line(left, bottom, left, bottom + grid_h, strokeColor=PALETTE["gray"], strokeWidth=0.7))
    drawing.add(Line(left + grid_w / 2, bottom, left + grid_w / 2, bottom + grid_h, strokeColor=PALETTE["warm_gray"], strokeWidth=0.5))
    drawing.add(Line(left, bottom + grid_h / 2, left + grid_w, bottom + grid_h / 2, strokeColor=PALETTE["warm_gray"], strokeWidth=0.5))
    drawing.add(String(left + grid_w / 2 - 25, 12, x_label, fontName=FONT_REGULAR, fontSize=8.5, fillColor=PALETTE["gray"]))
    drawing.add(String(2, bottom + grid_h / 2, y_label, fontName=FONT_REGULAR, fontSize=8.5, fillColor=PALETTE["gray"]))
    for item in items:
        x = left + max(0.3, min(5, x_getter(item))) / 5 * grid_w
        y = bottom + max(0.3, min(5, y_getter(item))) / 5 * grid_h
        drawing.add(Circle(x, y, 10, fillColor=PALETTE["gold"], strokeColor=PALETTE["deep_gold"], strokeWidth=0.8))
        drawing.add(String(x - 3, y - 3, str(label_getter(item)), fontName=FONT_BOLD, fontSize=8, fillColor=PALETTE["paper"]))
    return drawing


def score_rows(breakdown, kind):
    if kind == "asset":
        labels = [("问题价值", "problem_value", 25), ("结果证据", "result_evidence", 20), ("稀缺与护城河", "moat", 20), ("平台外可迁移性", "portability", 15), ("产品化成熟度", "product_readiness", 20)]
    else:
        labels = [("客户紧迫度", "customer_urgency", 25), ("经验匹配度", "experience_fit", 25), ("交付可控性", "delivery_control", 20), ("付款者清晰度", "buyer_clarity", 15), ("低成本验证", "low_cost_validation", 15)]
    return [[label, "待验证" if breakdown.get(key) is None else f"{breakdown[key]}/{maximum}"] for label, key, maximum in labels]


def score_strip(breakdown, kind, styles):
    """Compact five-factor scorecard for one-page asset profiles."""
    items = score_rows(breakdown, kind)
    cells = []
    for label, value in items:
        cells.append(Table([
            [p(label, styles["metric_label"])],
            [rich(f"<font color='#A96F00'><b>{esc(value)}</b></font>", styles["table_head"])],
        ], colWidths=[31.6 * mm]))
    table = Table([cells], colWidths=[32 * mm] * len(cells), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["soft_gold"]),
        ("BOX", (0, 0), (-1, -1), 0.45, PALETTE["warm_gray"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, PALETTE["warm_gray"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def heatmap_table(dimensions, styles):
    shades = {
        1: colors.HexColor("#F3F1EC"),
        2: colors.HexColor("#F8F0DA"),
        3: colors.HexColor("#F2E1B7"),
        4: colors.HexColor("#E8C66E"),
        5: colors.HexColor("#D89808"),
    }
    rows = [["护城河维度", "强度", "事实或推断依据", "当前限制"]]
    for item in dimensions:
        rows.append([item["name"], f"{item['level']}/5", item["evidence"], item["limitation"]])
    table = brand_table(rows, [30 * mm, 18 * mm, 58 * mm, 54 * mm], styles)
    commands = []
    for row_index, item in enumerate(dimensions, start=1):
        commands.extend([
            ("BACKGROUND", (1, row_index), (1, row_index), shades[item["level"]]),
            ("ALIGN", (1, row_index), (1, row_index), "CENTER"),
        ])
    table.setStyle(TableStyle(commands))
    return table


def price_ladder(stages, styles):
    cells = []
    for index, stage in enumerate(stages):
        body = f"<b>{esc(stage['stage'])}</b><br/><font color='#A96F00'>{esc(stage['price'])}</font><br/>{esc(stage['evidence_required'])}"
        cells.append(rich(body, styles["table"]))
    table = Table([cells], colWidths=[160 * mm / len(cells)] * len(cells), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["soft_gold"]),
        ("BOX", (0, 0), (-1, -1), 0.55, PALETTE["gold"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.55, PALETTE["gold"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def logo_flowable(path, width=44 * mm):
    if path and Path(path).exists():
        image = Image(str(path), width=width, height=width / 3)
        image.hAlign = "RIGHT"
        return image
    return Spacer(1, 1)


def page_chrome(canvas, doc, logo_path, report_title):
    if canvas.getPageNumber() == 1:
        return
    canvas.saveState()
    canvas.setStrokeColor(PALETTE["gold"])
    canvas.setLineWidth(0.8)
    canvas.line(18 * mm, A4[1] - 17 * mm, A4[0] - 18 * mm, A4[1] - 17 * mm)
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(PALETTE["gray"])
    canvas.drawString(18 * mm, A4[1] - 12.3 * mm, report_title)
    if logo_path and Path(logo_path).exists():
        canvas.drawImage(str(logo_path), A4[0] - 43 * mm, A4[1] - 15.2 * mm, width=23 * mm, height=7.7 * mm, mask="auto", preserveAspectRatio=True)
    canvas.setStrokeColor(PALETTE["warm_gray"])
    canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
    canvas.drawString(18 * mm, 10 * mm, "个人经验资产与高价值变现诊断 | 内部评估版")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"GULIAI | {canvas.getPageNumber():02d}")
    canvas.restoreState()


def add_cover(story, data, styles, logo_path):
    meta = data["meta"]
    story.extend([
        Spacer(1, 13 * mm),
        logo_flowable(logo_path, 52 * mm),
        Spacer(1, 24 * mm),
        p("EXPERIENCE ASSET DISTILLATION", styles["eyebrow"]),
        Spacer(1, 3 * mm),
        rich("个人经验资产与<br/>高价值变现诊断报告", styles["cover_title"]),
        HRFlowable(width="34%", thickness=3, color=PALETTE["gold"], hAlign="LEFT", spaceAfter=8 * mm),
        p("从职场经历中提炼可迁移、可交付、可定价的商业资产", styles["cover_sub"]),
        Spacer(1, 18 * mm),
        brand_table([
            ["被评估人", meta["name"]],
            ["报告编号", meta["report_id"]],
            ["评估日期", meta["date"]],
            ["核心标签", " / ".join(meta["keywords"])],
        ], [34 * mm, 108 * mm], styles, repeat_rows=0),
        Spacer(1, 22 * mm),
        focus_card("阅读说明", "本报告基于现有资料形成专业判断。价格、市场需求与高客单潜力属于待验证假设，不构成收益承诺。", styles),
        PageBreak(),
    ])


def add_chapter_1(story, data, styles):
    summary = data["executive_summary"]
    assets = data["top_assets"]
    section_header(story, 1, "核心诊断结论", summary["core_judgment"], styles)
    story.extend([
        subheading("1.1", "Top 3 经验资产排序", styles),
        Spacer(1, 2 * mm),
        ranking_chart(assets),
        Spacer(1, 4 * mm),
        metric_cards([(str(assets[0]["score_total"]), "最高资产价值指数"), (data["monetization_offers"][0]["priority"], "首选产品优先级"), ("验证期", "商业化阶段判断")], styles),
        Spacer(1, 2 * mm),
        focus_card("阶段判断", summary["opportunity_level"], styles),
        Spacer(1, 5 * mm),
        subheading("1.2", "首选客户与首选产品", styles),
        Spacer(1, 2 * mm),
        focus_card("首选客户", summary["best_customer"], styles),
        Spacer(1, 2 * mm),
        focus_card("首选产品", summary["best_offer"], styles),
        Spacer(1, 5 * mm),
        subheading("1.3", "变现原点", styles),
        Spacer(1, 2 * mm),
        brand_table([
            ["我有的", "别人需要的", "我愿意长期做的"],
            [summary["monetization_origin"]["what_i_have"], summary["monetization_origin"]["what_others_need"], summary["monetization_origin"]["what_i_want_long_term"]],
        ], [53 * mm, 53 * mm, 54 * mm], styles),
        Spacer(1, 3 * mm),
        focus_card("最大交集", summary["monetization_origin"]["intersection"], styles),
        Spacer(1, 4 * mm),
        subheading("1.4", "风险与判断边界", styles),
        Spacer(1, 2 * mm),
        brand_table([["当前最大风险", "判断边界"], [summary["main_risk"], summary["confidence_boundary"]]], [80 * mm, 80 * mm], styles),
        PageBreak(),
    ])


def add_chapter_2(story, data, styles):
    assets = data["top_assets"]
    section_header(story, 2, "Top 3 经验资产评估", "真正值钱的不是职位名称，而是能重复解决高价值问题的关键判断、方法和交付物。", styles)
    story.extend([
        matrix_chart(
            assets,
            lambda item: item["score_breakdown"]["result_evidence"] / 4,
            lambda item: item["score_breakdown"]["problem_value"] / 5,
            lambda item: item["rank"],
            "结果证据 →", "问题价值 ↑", "经验资产价值矩阵｜右上区域优先商业化",
        ),
        Spacer(1, 3 * mm),
        p("图中数字对应资产排名。资产 3 问题价值较高，但结果证据明显不足，应先补案例而不是直接高价销售。", styles["muted"]),
        brand_table(
            [["排名", "经验资产", "价值指数", "当前判断"]]
            + [[f"#{item['rank']}", item["name"], str(item["score_total"]), item["maturity"]] for item in assets],
            [18 * mm, 82 * mm, 25 * mm, 35 * mm], styles, compact=True,
        ),
        Spacer(1, 4 * mm),
        PageBreak(),
    ])
    for index, asset in enumerate(assets):
        if index:
            story.append(PageBreak())
        story.extend([
            subheading(f"2.{asset['rank']}", asset["name"], styles),
            Spacer(1, 2 * mm),
            metric_cards([(str(asset["score_total"]), "资产价值指数"), (asset["maturity"], "资产成熟度"), (f"#{asset['rank']}", "综合排序")], styles),
            Spacer(1, 4 * mm),
            focus_card("高价值问题", asset["high_value_problem"], styles),
            Spacer(1, 3 * mm),
            paired_table([
                ["来源经历", "场景与挑战"],
                [asset["source_experience"], f"{asset['scene']}\n挑战：{asset['challenge']}"],
                ["个人责任", "关键决策"],
                [asset["personal_role"], asset["key_decision"]],
            ], [80 * mm, 80 * mm], styles, compact=True),
            Spacer(1, 3 * mm),
            paired_table([
                ["反常识洞察", "解题机制"],
                [asset["counterintuitive_insight"], asset["solution_mechanism"]],
                ["结果证据", "可迁移性与护城河"],
                [asset["result_evidence"], f"{asset['portability']}\n护城河：{asset['moat']}"],
            ], [80 * mm, 80 * mm], styles, compact=True),
            Spacer(1, 3 * mm),
            score_strip(asset["score_breakdown"], "asset", styles),
            Spacer(1, 3 * mm),
            brand_table([
                ["现在可以卖", "当前不能承诺"],
                [bullets(asset["can_sell"]), bullets(asset["cannot_promise"])],
            ], [80 * mm, 80 * mm], styles, compact=True),
            Spacer(1, 3 * mm),
            focus_card("下一条关键证据", asset["evidence_gap"], styles),
        ])
    story.append(PageBreak())


def add_chapter_3(story, data, styles):
    moat = data["moat_analysis"]
    section_header(story, 3, "护城河与不可替代性", moat["conclusion"], styles)
    story.extend([
        subheading("3.1", "七维护城河热力表", styles),
        Spacer(1, 2 * mm),
        heatmap_table(moat["dimensions"], styles),
        Spacer(1, 5 * mm),
        subheading("3.2", "可带走资产与平台资产", styles),
        Spacer(1, 2 * mm),
        brand_table([
            ["离开原平台仍可带走", "不能直接当成个人能力"],
            [bullets(moat["portable_assets"]), bullets(moat["platform_assets"])],
        ], [80 * mm, 80 * mm], styles),
        PageBreak(),
    ])


def add_chapter_4(story, data, styles):
    customers = data["customer_segments"]
    section_header(story, 4, "高价值问题与付费客户", "优先服务需求触发明确、问题代价可感知、付款者清晰且与 Top 3 资产直接匹配的人群。", styles)
    story.extend([
        matrix_chart(customers, lambda item: item["payment_score"], lambda item: item["urgency_score"], lambda item: item["rank"], "付款能力与决策权 →", "问题紧迫度 ↑", "客户紧迫度矩阵｜右上区域优先服务"),
        Spacer(1, 3 * mm),
        p("数字对应客户排序。供应链团队问题潜力较高，但与个人案例的匹配证据仍弱，暂不作为首选客户。", styles["muted"]),
        Spacer(1, 4 * mm),
        PageBreak(),
    ])
    for customer in customers:
        story.append(KeepTogether([
            subheading(f"4.{customer['rank']}", customer["name"], styles),
            Spacer(1, 1.5 * mm),
            paired_table([
                ["具体人群", "需求触发", "置信度"],
                [customer["people"], customer["trigger"], customer["confidence"]],
                ["表面问题", "深层问题", "不解决代价"],
                [customer["surface_problem"], customer["deep_problem"], customer["cost_of_inaction"]],
            ], [54 * mm, 63 * mm, 43 * mm], styles, compact=True),
            Spacer(1, 1.5 * mm),
            paired_table([
                ["当前替代", "使用者", "付款者/审批者"],
                [customer["current_alternative"], customer["user"], f"{customer['buyer']} / {customer['approver']}"],
                ["购买理由", "匹配资产", "矩阵坐标"],
                [customer["buying_reason"], customer["matching_asset"], f"紧迫 {customer['urgency_score']}/5｜付费 {customer['payment_score']}/5"],
            ], [65 * mm, 48 * mm, 47 * mm], styles, compact=True),
            Spacer(1, 3 * mm),
        ]))
    story.extend([
        focus_card("服务顺序", "先服务客户 1 验证诊断付费，再以客户 2 承接工作坊现金流；客户 3 只做探索访谈，补齐本人主导案例前不作为主定位。", styles),
        Spacer(1, 3 * mm),
    ])
    story.append(PageBreak())


def add_chapter_5(story, data, styles):
    offers = data["monetization_offers"]
    section_header(story, 5, "变现切入点与产品清单", "优先级不是看产品听起来多高级，而是看客户问题、经验匹配、交付边界和低成本验证能否同时成立。", styles)
    story.extend([
        matrix_chart(
            offers,
            lambda item: item["score_breakdown"]["delivery_control"] / 4,
            lambda item: (item["score_breakdown"]["customer_urgency"] + item["score_breakdown"]["experience_fit"] + item["score_breakdown"]["buyer_clarity"]) / 13,
            lambda item: item["rank"],
            "交付可控性 →", "商业价值潜力 ↑", "产品优先级矩阵｜右上区域优先测试",
        ),
        Spacer(1, 3 * mm),
        brand_table(
            [["排名", "产品", "类型", "得分", "产品优先级", "可行性"]] + [[str(item["rank"]), item["name"], item["category"], str(item["score_total"]), item["priority"], item["feasibility"]] for item in offers],
            [13 * mm, 55 * mm, 25 * mm, 16 * mm, 22 * mm, 29 * mm], styles, compact=True,
        ),
        Spacer(1, 5 * mm),
        PageBreak(),
    ])
    for index, offer in enumerate(offers):
        if index:
            story.append(PageBreak())
        story.extend([
            subheading(f"5.{offer['rank']}", f"[{offer['priority']}] {offer['name']}", styles),
            Spacer(1, 2 * mm),
            metric_cards([(str(offer["score_total"]), "产品优先级得分"), (offer["priority"], "推荐等级"), (offer["feasibility"], "当前可行性")], styles),
            Spacer(1, 2 * mm),
            score_strip(offer["score_breakdown"], "product", styles),
            Spacer(1, 3 * mm),
            brand_table([
                ["服务对象与触发", "付费问题与代价"],
                [f"{offer['audience']}\n触发：{offer['trigger']}", f"{offer['paid_problem']}\n代价：{offer['cost_of_inaction']}"]
            ], [80 * mm, 80 * mm], styles, compact=True),
            Spacer(1, 2 * mm),
            brand_table([
                ["方法机制", "AI 的真实作用", "交付物"],
                [offer["mechanism"], offer["ai_role"], bullets(offer["deliverables"])],
            ], [55 * mm, 50 * mm, 55 * mm], styles, compact=True),
            Spacer(1, 2 * mm),
            paired_table([
                ["测试价格", "定价依据"],
                [offer["price_test"], offer["pricing_basis"]],
                ["服务边界", "高客单升级条件"],
                [offer["scope_excluded"], offer["high_ticket_condition"]],
            ], [80 * mm, 80 * mm], styles, compact=True),
            Spacer(1, 2 * mm),
            focus_card("验证动作", f"{offer['validation_action']}\n建议：{offer['recommendation']}", styles),
            Spacer(1, 5 * mm),
        ])
    story.append(PageBreak())


def add_chapter_6(story, data, styles):
    offer = data["primary_offer"]
    section_header(story, 6, "首选产品设计", offer["why_first"], styles)
    story.extend([
        subheading("6.1", offer["offer_name"], styles),
        Spacer(1, 2 * mm),
        focus_card("一句话定位", offer["positioning"], styles),
        Spacer(1, 4 * mm),
        paired_table([
            ["客户需要提供", "交付步骤", "可见交付物"],
            [bullets(offer["customer_inputs"]), bullets(offer["steps"]), bullets(offer["deliverables"])],
        ], [48 * mm, 54 * mm, 58 * mm], styles),
        Spacer(1, 4 * mm),
        subheading("6.2", "价格升级阶梯", styles),
        Spacer(1, 2 * mm),
        price_ladder(offer["price_ladder"], styles),
        Spacer(1, 4 * mm),
        brand_table([
            ["明确不做", "成功信号"],
            [offer["scope_excluded"], offer["success_signal"]],
            ["停止/调整条件", "下一步升级"],
            [offer["stop_condition"], offer["next_upgrade"]],
        ], [80 * mm, 80 * mm], styles),
        PageBreak(),
    ])


def add_chapter_7(story, data, styles):
    interview = data["expert_interview"]
    section_header(story, 7, "专家访谈追问", interview["thickness_note"], styles)
    story.extend([
        metric_cards([(str(len(interview["questions"])), "高杠杆问题"), ("需要" if interview["needs_interview"] else "不需要", "是否触发访谈"), (interview["status"], "当前访谈状态")], styles),
        Spacer(1, 5 * mm),
    ])
    for index, item in enumerate(interview["questions"], start=1):
        story.append(KeepTogether([
            subheading(f"7.{index}", item["question"], styles),
            Spacer(1, 2 * mm),
            paired_table([
                ["为什么问", "需要的材料"],
                [item["why_ask"], item["requested_evidence"]],
                ["会改变什么", "未回答时的保守判断"],
                [item["decision_affected"], item["fallback_assumption"]],
            ], [80 * mm, 80 * mm], styles, compact=True),
            Spacer(1, 5 * mm),
        ]))
    story.extend([
        focus_card("访谈后如何使用", "每个回答只重算它能够改变的资产得分、产品优先级与价格上限；没有新证据的部分保持原判断，不因为叙述更精彩而整体抬高评价。", styles),
        Spacer(1, 3 * mm),
        brand_table([
            ["优先提交", "不作为结果证据"],
            ["项目复盘、本人决策、作品、客户采用、复购或采购记录", "泛泛自评、学员好评、知名客户名称、未经授权的项目归因"],
        ], [80 * mm, 80 * mm], styles, compact=True),
    ])
    story.append(PageBreak())


def add_chapter_8(story, data, styles):
    section_header(story, 8, "商业化行动路径", "路线按证据成熟度推进：先验证最值钱的资产，再复用交付，最后才扩大高客单与方法品牌。", styles)
    for index, stage in enumerate(data["roadmap"], start=1):
        story.append(KeepTogether([
            subheading(f"8.{index}", stage["stage"], styles),
            Spacer(1, 2 * mm),
            paired_table([
                ["进入条件", "阶段目标", "关键行动"],
                [stage["entry_condition"], stage["objective"], bullets(stage["actions"])],
                ["产出资产", "决策闸门", "主要风险"],
                [bullets(stage["outputs"]), stage["decision_gate"], stage["risk"]],
            ], [53 * mm, 53 * mm, 54 * mm], styles, compact=True),
            Spacer(1, 6 * mm),
        ]))
    story.extend([
        focus_card("推进原则", "短期、中期、长期是证据阶段，不是机械日历。只有通过上一阶段决策闸门，才进入下一阶段；未通过时应缩小范围、补证据或调整产品。", styles),
        Spacer(1, 3 * mm),
        brand_table([
            ["继续", "调整", "停止"],
            ["目标客户确认问题价值并愿意付费", "有需求但交付边界、价格或人群不匹配", "连续验证仍无预算、无访谈或无法形成可见结果"],
        ], [53 * mm, 53 * mm, 54 * mm], styles, compact=True),
    ])
    story.append(PageBreak())


def add_chapter_9(story, data, styles):
    section_header(story, 9, "证据与使用边界", "所有商业判断都必须能回链到用户事实、模型推断、待验证假设或行动建议；缺少授权和结果证据时保持保守。", styles)
    rows = [["编号/类型", "主张", "来源与状态", "授权/限制"]]
    for item in data["evidence_ledger"]:
        rows.append([
            f"{item['id']}\n{item['classification']}",
            item["claim"],
            f"{item['source']}\n状态：{item['status']}",
            f"{item['authorization']}\n限制：{item['limitation']}",
        ])
    story.extend([
        subheading("9.1", "来源台账", styles),
        Spacer(1, 2 * mm),
        brand_table(rows, [26 * mm, 49 * mm, 43 * mm, 42 * mm], styles, compact=True),
        Spacer(1, 3 * mm),
        focus_card("下一版升级条件", "补齐关键项目复盘、客户授权、复购或采购记录、训后采用证据和本人长期意愿后，只更新受影响的资产、产品与价格判断。", styles),
        Spacer(1, 5 * mm),
        subheading("9.2", "升级清单与使用边界", styles),
        Spacer(1, 2 * mm),
        brand_table([
            ["必须补齐", "完成后重算", "始终不承诺"],
            ["本人主导的关键项目、可核验结果、客户授权、长期投入意愿", "Top 3 排名、产品优先级、价格测试区间和高客单升级条件", "未经验证的收入结果、普遍转化率、客户采购结果或超出能力边界的实施结果"],
        ], [54 * mm, 53 * mm, 53 * mm], styles, compact=True),
        Spacer(1, 5 * mm),
        focus_card("报告结论", "现阶段最优策略不是立刻包装高价课程，而是用边界清楚的诊断与岗位实战工作坊验证付费，再把重复交付沉淀成咨询产品和方法资产。", styles),
    ])


def generate_report(data, output_path, logo_path=None):
    validate_report_data(data)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    report_title = f"{data['meta']['name']} | 个人经验资产与高价值变现诊断报告"
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=report_title,
        author="GULIAI",
        subject="Top 3 经验资产、付费客户、产品设计与验证路径",
    )
    story = []
    add_cover(story, data, styles, logo_path)
    add_chapter_1(story, data, styles)
    add_chapter_2(story, data, styles)
    add_chapter_3(story, data, styles)
    add_chapter_4(story, data, styles)
    add_chapter_5(story, data, styles)
    add_chapter_6(story, data, styles)
    add_chapter_7(story, data, styles)
    add_chapter_8(story, data, styles)
    add_chapter_9(story, data, styles)
    chrome = lambda canvas, current_doc: page_chrome(canvas, current_doc, logo_path, report_title)
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True, help="报告数据 JSON")
    parser.add_argument("--output", required=True, help="输出 PDF")
    parser.add_argument("--logo", default=str(ROOT / "assets" / "guliai-logo-transparent.png"))
    args = parser.parse_args()
    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    output = generate_report(data, args.output, args.logo)
    print(f"PDF 报告已生成: {output}")


if __name__ == "__main__":
    main()
