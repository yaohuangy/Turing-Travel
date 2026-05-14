import io
import logging
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(),
)

# Try to register a Chinese font for PDF
_CHINESE_FONT_NAME = "Helvetica"
_CHINESE_FONT_PATHS = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/STSONG.TTF",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
]


def _register_font():
    for path in _CHINESE_FONT_PATHS:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("CJK", path))
                return "CJK"
            except Exception:
                continue
    return "Helvetica"


_CHINESE_FONT_NAME = _register_font()
logger.info("PDF Chinese font: %s", _CHINESE_FONT_NAME)


def export_markdown(itinerary: dict) -> str:
    """Render itinerary to Markdown using Jinja2 template."""
    template = jinja_env.get_template("trip.md.j2")
    return template.render(**itinerary)


def export_pdf(itinerary: dict) -> bytes:
    """Generate a PDF file for the itinerary."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    elements = _build_pdf_elements(itinerary)
    doc.build(elements)
    return buf.getvalue()


def _cjk_style(name: str, **kwargs) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=_CHINESE_FONT_NAME, **kwargs)


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _build_pdf_elements(data: dict) -> list:
    styles = getSampleStyleSheet()
    title_style = _cjk_style("CJKTitle", fontSize=18, leading=24, spaceAfter=12, alignment=1)
    h2_style = _cjk_style("CJKH2", fontSize=14, leading=18, spaceBefore=12, spaceAfter=6)
    body_style = _cjk_style("CJKBody", fontSize=10, leading=14, spaceAfter=4)
    elements = []

    # Title
    elements.append(_p(f"{data['destination']} 旅行行程", title_style))
    elements.append(_p(f"日期：{data['start_date']} ~ {data['end_date']}", body_style))
    elements.append(Spacer(1, 6 * mm))

    # Days
    for day in data.get("days", []):
        elements.append(_p(f"第 {day['day_index'] + 1} 天 — {day['date']}", h2_style))

        w = day.get("weather")
        if w:
            elements.append(_p(f"天气：{w['condition']}，{w['temp_low']}°C ~ {w['temp_high']}°C", body_style))

        spots = day.get("spots", [])
        if spots:
            elements.append(_p("景点：", body_style))
            for spot in spots:
                addr = f" — {spot['address']}" if spot.get("address") else ""
                elements.append(_p(f"  • {spot['name']}（{spot.get('visit_duration', '')}）{addr}", body_style))

        meals = day.get("meals", [])
        if meals:
            meal_map = {m["type"]: m["name"] for m in meals}
            elements.append(_p(f"早餐：{meal_map.get('breakfast', '—')}  午餐：{meal_map.get('lunch', '—')}  晚餐：{meal_map.get('dinner', '—')}", body_style))

        hotel = day.get("hotel")
        if hotel:
            elements.append(_p(f"住宿：{hotel['name']}（{hotel.get('location', '')}）— ¥{hotel.get('estimated_price', 0)}/晚", body_style))

        route = day.get("route_estimate")
        if route:
            elements.append(_p(f"交通：驾车约 {route['distance_km']} km，预计 {route['duration_min']} 分钟", body_style))

        elements.append(Spacer(1, 4 * mm))

    # Budget table
    elements.append(Spacer(1, 8 * mm))
    elements.append(_p("预算明细", h2_style))
    budget = data.get("budget", {})
    table_data = [
        ["项目", "费用（元）"],
        ["交通", str(budget.get("transportation", 0))],
        ["住宿", str(budget.get("accommodation", 0))],
        ["餐饮", str(budget.get("meals", 0))],
        ["门票", str(budget.get("tickets", 0))],
        ["其他", str(budget.get("other", 0))],
        ["总计", str(budget.get("total", 0))],
    ]
    table = Table(table_data, colWidths=[80 * mm, 80 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _CHINESE_FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(table)

    return elements
