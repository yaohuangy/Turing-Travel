import json
import logging
import re
from datetime import timedelta

import dashscope
from dashscope import Generation

from app.config import settings
from app.models.schemas import TripRequest

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency at module level
_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        from rag import retriever
        _retriever = retriever
    return _retriever


def _build_rag_query(req: TripRequest) -> str:
    """Build a retrieval query from the trip request."""
    parts = [req.destination]
    parts.extend(req.preferences)
    if req.extra_requirements:
        parts.append(req.extra_requirements)
    return " ".join(parts)


def _retrieve_context(req: TripRequest) -> str:
    """Retrieve relevant travel guide chunks for the given request."""
    try:
        ret = _get_retriever()
        query = _build_rag_query(req)
        chunks = ret.retrieve(query, req.destination, top_k=5, use_rerank=True)
        if not chunks:
            logger.info("No RAG chunks found for %s", req.destination)
            return ""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[参考{i}] {chunk['content']}")
        context = "\n\n".join(context_parts)
        logger.info(
            "Retrieved %d RAG chunks for %s (total %d chars)",
            len(chunks), req.destination, len(context),
        )
        return context
    except Exception as e:
        logger.warning("RAG retrieval failed for %s: %s", req.destination, e)
        return ""

SYSTEM_PROMPT = """你是一个专业的旅行规划师。根据用户的需求，生成一份结构化的多日旅行行程。

你必须严格按以下 JSON Schema 输出（只输出 JSON，不要任何额外文字）：

{
  "destination": "城市名",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "day_index": 0,
      "date": "YYYY-MM-DD",
      "weather": null,
      "spots": [
        {
          "name": "景点名称",
          "address": "",
          "location": null,
          "visit_duration": "2小时",
          "description": "简要描述",
          "image_url": null,
          "poi_id": null
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "推荐早餐", "description": "简要描述"},
        {"type": "lunch", "name": "推荐午餐", "description": "简要描述"},
        {"type": "dinner", "name": "推荐晚餐", "description": "简要描述"}
      ],
      "hotel": {
        "name": "推荐酒店",
        "location": "位置区域",
        "estimated_price": 300
      }
    }
  ],
  "budget": {
    "total": 0,
    "transportation": 0,
    "accommodation": 0,
    "meals": 0,
    "tickets": 0,
    "other": 0
  }
}

规则：
1. day_index 从 0 开始
2. 每天安排 2-5 个景点，景点顺序要合理（考虑地理位置相邻）
3. 根据预算档位调整推荐：economy 偏低消费，comfort 中等，luxury 高端
4. budget 各项单位为人民币元，total 为各项之和
5. 景点名称使用真实存在的景点
6. 如果用户提供了额外需求，尽量满足
7. weather 字段统一设为 null
8. location、image_url、poi_id 字段统一设为 null"""


def _build_user_prompt(req: TripRequest, rag_context: str = "") -> str:
    days_count = (req.end_date - req.start_date).days
    budget_label = {"economy": "经济型", "comfort": "舒适型", "luxury": "豪华型"}[req.budget_level]
    prefs = "、".join(req.preferences) if req.preferences else "无特殊偏好"
    extra = req.extra_requirements or "无"
    prompt = (
        f"请为我规划一趟旅行：\n"
        f"- 目的地：{req.destination}\n"
        f"- 日期：{req.start_date} 至 {req.end_date}（共 {days_count} 天）\n"
        f"- 预算档位：{budget_label}\n"
        f"- 出行人数：{req.travelers} 人\n"
        f"- 兴趣偏好：{prefs}\n"
        f"- 额外需求：{extra}\n"
    )
    if rag_context:
        prompt += f"\n--- 以下为{req.destination}本地旅行攻略参考，请参考其中景点、美食、住宿信息来规划行程 ---\n\n{rag_context}\n\n--- 参考结束，请根据以上信息规划行程 ---\n"
    prompt += "\n请输出 JSON。"
    return prompt


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response, handling various edge cases."""
    text = text.strip()
    # Remove markdown code fences
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    # Try to find balanced braces
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")
    # Count braces to find the matching closing brace
    depth = 0
    end = -1
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        raise ValueError("Unbalanced JSON braces in response")
    text = text[start : end + 1]
    return json.loads(text)


def _normalize(data: dict) -> dict:
    """Normalize LLM output to match Pydantic types.

    DeepSeek models sometimes emit `[]` for empty string fields.
    """
    STRING_FIELDS = {"name", "address", "visit_duration", "description", "condition", "wind", "type", "date"}
    NULLABLE_FIELDS = {"image_url", "poi_id", "location", "weather", "hotel", "route_estimate"}

    def _fix(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, list) and len(v) == 0:
                    if k in STRING_FIELDS:
                        obj[k] = ""
                    elif k in NULLABLE_FIELDS:
                        obj[k] = None
                elif isinstance(v, (dict, list)):
                    _fix(v)
        elif isinstance(obj, list):
            for item in obj:
                _fix(item)

    _fix(data)
    return data


def _build_fallback_itinerary(req: TripRequest) -> dict:
    """Build a minimal valid itinerary when LLM generation fails completely."""
    logger.warning("Building fallback itinerary for %s", req.destination)
    days_count = (req.end_date - req.start_date).days
    days = []
    current_date = req.start_date
    for i in range(days_count):
        days.append({
            "day_index": i,
            "date": current_date.isoformat(),
            "weather": None,
            "spots": [
                {
                    "name": f"{req.destination}景点{j+1}",
                    "address": "",
                    "location": None,
                    "visit_duration": "2小时",
                    "description": "",
                    "image_url": None,
                    "poi_id": None,
                }
                for j in range(2)
            ],
            "meals": [
                {"type": "breakfast", "name": "当地早餐", "description": ""},
                {"type": "lunch", "name": "当地午餐", "description": ""},
                {"type": "dinner", "name": "当地晚餐", "description": ""},
            ],
            "hotel": {"name": "推荐酒店", "location": req.destination, "estimated_price": 300},
        })
        current_date += timedelta(days=1)

    return {
        "destination": req.destination,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "days": days,
        "budget": {
            "total": days_count * 800,
            "transportation": days_count * 150,
            "accommodation": days_count * 300,
            "meals": days_count * 200,
            "tickets": days_count * 100,
            "other": days_count * 50,
        },
    }


def generate_itinerary(req: TripRequest) -> dict:
    """Generate a travel itinerary using the configured LLM. Returns raw JSON dict."""
    # Retrieve RAG context
    rag_context = _retrieve_context(req)

    dashscope.api_key = settings.DASHSCOPE_API_KEY
    user_prompt = _build_user_prompt(req, rag_context)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for attempt in range(1, 4):
        try:
            logger.info(
                "LLM generation attempt %d/3 for destination=%s, days=%s~%s",
                attempt, req.destination, req.start_date, req.end_date,
            )
            resp = Generation.call(
                model=settings.LLM_MODEL,
                messages=messages,
                result_format="message",
            )
            if resp.status_code != 200:
                raise RuntimeError(f"DashScope API error: code={resp.status_code}, message={resp.message}")

            usage = resp.usage
            logger.info(
                "Token usage (attempt %d): input=%s, output=%s",
                attempt, usage.input_tokens, usage.output_tokens,
            )

            content = resp.output.choices[0].message.content
            result = _normalize(_extract_json(content))
            logger.info("LLM generation succeeded on attempt %d", attempt)
            return result

        except Exception as e:
            last_error = e
            logger.warning("LLM generation attempt %d failed: %s", attempt, e)
            if attempt < 3:
                continue

    logger.error("LLM generation failed after 3 attempts, using fallback: %s", last_error)
    return _build_fallback_itinerary(req)
