from app.services import export_service

SAMPLE = {
    "destination": "杭州",
    "start_date": "2026-06-01",
    "end_date": "2026-06-02",
    "days": [
        {
            "day_index": 0,
            "date": "2026-06-01",
            "weather": {"condition": "晴", "temp_high": 28, "temp_low": 18, "wind": "东南 ≤3"},
            "spots": [
                {"name": "西湖", "address": "杭州市西湖区", "location": None, "visit_duration": "3小时", "description": "世界文化遗产", "image_url": None, "poi_id": None},
                {"name": "灵隐寺", "address": "杭州市西湖区", "location": None, "visit_duration": "2小时", "description": "千年古刹", "image_url": None, "poi_id": None},
            ],
            "meals": [
                {"type": "breakfast", "name": "小笼包", "description": ""},
                {"type": "lunch", "name": "西湖醋鱼", "description": ""},
                {"type": "dinner", "name": "东坡肉", "description": ""},
            ],
            "hotel": {"name": "西湖酒店", "location": "西湖区", "estimated_price": 400},
            "route_estimate": {"distance_km": 5.5, "duration_min": 15},
        }
    ],
    "budget": {"total": 2000, "transportation": 300, "accommodation": 400, "meals": 500, "tickets": 300, "other": 500},
}


def test_export_markdown_contains_key_info():
    md = export_service.export_markdown(SAMPLE)
    assert "# 杭州 旅行行程" in md
    assert "## 第 1 天" in md
    assert "西湖" in md
    assert "灵隐寺" in md
    assert "晴天" in md or "28" in md  # weather
    assert "西湖醋鱼" in md
    assert "2000" in md
    assert "**总计**" in md


def test_export_pdf_returns_bytes():
    pdf = export_service.export_pdf(SAMPLE)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 0
    # PDF magic bytes
    assert pdf[:4] == b"%PDF"
