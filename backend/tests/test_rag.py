"""Tests for RAG pipeline: vector_db and retriever."""
from unittest.mock import MagicMock, patch

import pytest

from app.agents.trip_planner_agent import _build_rag_query, _build_user_prompt
from app.models.schemas import TripRequest
from rag import retriever as ret_mod
from rag import vector_db


@pytest.fixture
def sample_request():
    return TripRequest(
        destination="大理",
        start_date="2026-06-01",
        end_date="2026-06-03",
        budget_level="comfort",
        travelers=2,
        preferences=["自然风光", "美食探店"],
        extra_requirements="想去洱海边",
    )


def test_build_rag_query(sample_request):
    query = _build_rag_query(sample_request)
    assert "大理" in query
    assert "自然风光" in query
    assert "美食探店" in query
    assert "洱海" in query


def test_user_prompt_includes_rag_context(sample_request):
    rag_context = "[参考1] 洱海是云南第二大淡水湖，环湖一周约130公里。\n[参考2] 大理酸辣鱼是当地特色美食。"
    prompt = _build_user_prompt(sample_request, rag_context)
    assert "本地旅行攻略参考" in prompt
    assert "[参考1]" in prompt
    assert "[参考2]" in prompt
    assert "大理" in prompt


def test_user_prompt_without_rag(sample_request):
    prompt = _build_user_prompt(sample_request, "")
    assert "本地旅行攻略参考" not in prompt
    assert "大理" in prompt


def test_rule_rewrite():
    result = ret_mod._rule_rewrite("我想去杭州看西湖吃美食", "杭州")
    assert "杭州" in result
    assert "美食" in result


def test_rerank_fallback_on_error():
    candidates = [
        {"id": "c1", "content": "doc1", "score": 0.9},
        {"id": "c2", "content": "doc2", "score": 0.8},
        {"id": "c3", "content": "doc3", "score": 0.7},
        {"id": "c4", "content": "doc4", "score": 0.6},
    ]
    result = ret_mod._rerank("query", candidates)
    # Should return top 3 even if rerank fails (no API call made)
    assert 0 < len(result) <= 3


def test_vector_db_search_requires_data():
    """Search returns empty when no data indexed. This is expected before add_documents."""
    results = vector_db.search("test", "nonexistent_city", top_k=3)
    assert isinstance(results, list)
