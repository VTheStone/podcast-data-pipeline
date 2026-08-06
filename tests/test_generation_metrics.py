"""
Unit tests for tests/generation_metrics.py.
Covers only the pure functions — no Groq API calls, so these run fast
and for free as part of the normal pytest suite.
"""

import json

import pytest

from tests.generation_metrics import build_judge_user_prompt, parse_judge_response


def test_build_judge_user_prompt_numbers_context_chunks():
    prompt = build_judge_user_prompt(
        question="Qual a pergunta?",
        context_chunks=["primeiro trecho", "segundo trecho"],
        answer="Uma resposta.",
        reference_answer="O gabarito.",
    )

    assert "[1] primeiro trecho" in prompt
    assert "[2] segundo trecho" in prompt


def test_build_judge_user_prompt_includes_all_four_sections():
    prompt = build_judge_user_prompt("Q?", ["ctx"], "A.", "Ref.")

    assert "QUESTION:" in prompt
    assert "CONTEXT:" in prompt
    assert "ANSWER:" in prompt
    assert "REFERENCE_ANSWER:" in prompt


def test_build_judge_user_prompt_handles_empty_context():
    prompt = build_judge_user_prompt("Q?", [], "A.", "Ref.")

    assert "(no context retrieved)" in prompt


def test_parse_judge_response_plain_json():
    raw = '{"faithfulness": 5, "answer_relevancy": 4, "answer_correctness": 3, "reasoning": "ok"}'

    result = parse_judge_response(raw)

    assert result["faithfulness"] == 5
    assert result["answer_relevancy"] == 4
    assert result["answer_correctness"] == 3
    assert result["reasoning"] == "ok"


def test_parse_judge_response_strips_markdown_fence():
    raw = '```json\n{"faithfulness": 1, "answer_relevancy": 2, "answer_correctness": 1, "reasoning": "bad"}\n```'

    result = parse_judge_response(raw)

    assert result["faithfulness"] == 1


def test_parse_judge_response_defaults_missing_reasoning():
    raw = '{"faithfulness": 3, "answer_relevancy": 3, "answer_correctness": 3}'

    assert parse_judge_response(raw)["reasoning"] == ""


def test_parse_judge_response_rejects_score_above_range():
    raw = '{"faithfulness": 9, "answer_relevancy": 3, "answer_correctness": 3}'

    with pytest.raises(ValueError, match="out of range"):
        parse_judge_response(raw)


def test_parse_judge_response_rejects_score_below_range():
    raw = '{"faithfulness": 0, "answer_relevancy": 3, "answer_correctness": 3}'

    with pytest.raises(ValueError, match="out of range"):
        parse_judge_response(raw)


def test_parse_judge_response_raises_on_missing_field():
    raw = '{"faithfulness": 3, "answer_relevancy": 3}'

    with pytest.raises(KeyError):
        parse_judge_response(raw)


def test_parse_judge_response_raises_on_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        parse_judge_response("not json at all")