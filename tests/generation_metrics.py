"""
LLM-as-judge metrics for generation quality (M4).

Scores three standard RAG evaluation dimensions (same vocabulary used by
RAGAS) on a 1-5 scale, each judged against a different reference:

- faithfulness       -> judged against the retrieved CONTEXT (anti-hallucination)
- answer_relevancy   -> judged against the QUESTION
- answer_correctness -> judged against the golden REFERENCE_ANSWER

Uses the Groq client already configured for the project rather than
pulling in a LangChain-based evaluation framework. See
docs/phase8/overview.md for the RAGAS trade-off decision.

Judge calls run at temperature 0.0 with JSON mode to reduce variance, but
LLM-as-judge is never fully deterministic — treat scores as a monitored
metric with a regression tolerance, not as a binary pass/fail gate.
"""

import json

SCORE_FIELDS = ("faithfulness", "answer_relevancy", "answer_correctness")

JUDGE_SYSTEM_PROMPT = """You are a strict evaluator of RAG system answers. You output ONLY valid JSON.

You score three dimensions, each an integer from 1 to 5:

1. "faithfulness" - Is every factual claim in the ANSWER supported by the CONTEXT?
   5 = every claim traceable to the context. 1 = major claims invented (hallucinated).
   Judge ONLY against the context, never against your own world knowledge.

2. "answer_relevancy" - Does the ANSWER actually address the QUESTION?
   5 = directly and completely answers it. 1 = off-topic or evasive.
   An answer can be relevant even if factually wrong.

3. "answer_correctness" - Does the ANSWER agree with the REFERENCE_ANSWER?
   5 = same substance. 1 = contradicts it or misses its core content.
   Wording may differ; judge meaning, not phrasing.

Special case: if the REFERENCE_ANSWER states the information is not available,
then a correct ANSWER is one that also refuses / admits it lacks the information.
Score such a refusal HIGH on all three dimensions.

Output format (JSON only, no markdown fence):
{"faithfulness": <int>, "answer_relevancy": <int>, "answer_correctness": <int>, "reasoning": "<one sentence>"}"""


def build_judge_user_prompt(
    question: str,
    context_chunks: list[str],
    answer: str,
    reference_answer: str,
) -> str:
    """
    Assembles the judge's user message. Pure function — no API call.

    Args:
        question: The original user query.
        context_chunks: Raw texts of the chunks fed to the RAG prompt.
        answer: The answer the RAG pipeline produced.
        reference_answer: Hand-written gold answer from the golden dataset.

    Returns:
        Formatted prompt string with numbered context blocks.
    """
    if context_chunks:
        context = "\n\n".join(
            f"[{i}] {text}" for i, text in enumerate(context_chunks, start=1)
        )
    else:
        context = "(no context retrieved)"

    return f"""QUESTION:
{question}

CONTEXT:
{context}

ANSWER:
{answer}

REFERENCE_ANSWER:
{reference_answer}"""


def parse_judge_response(raw: str) -> dict:
    """
    Parses the judge's JSON reply, tolerating markdown code fences.
    Pure function — no API call.

    Args:
        raw: Raw string returned by the judge model.

    Returns:
        Dict with the three integer scores plus "reasoning".

    Raises:
        ValueError: If any score is outside the 1-5 range.
        KeyError: If a required score field is missing.
        json.JSONDecodeError: If the payload isn't valid JSON.
    """
    text = raw.strip()

    if text.startswith("```"):
        text = "\n".join(
            line for line in text.splitlines() if not line.strip().startswith("```")
        ).strip()

    data = json.loads(text)

    result = {}
    for field in SCORE_FIELDS:
        score = int(data[field])
        if not 1 <= score <= 5:
            raise ValueError(f"{field} out of range 1-5: {score}")
        result[field] = score

    result["reasoning"] = data.get("reasoning", "")
    return result


def judge_answer(
    client,
    model: str,
    question: str,
    context_chunks: list[str],
    answer: str,
    reference_answer: str,
) -> dict:
    """
    Sends one answer to the judge model and returns its scores.

    Args:
        client: A Groq client instance.
        model: Model id to use as judge.
        question: The original user query.
        context_chunks: Raw texts of the chunks fed to the RAG prompt.
        answer: The answer the RAG pipeline produced.
        reference_answer: Hand-written gold answer from the golden dataset.

    Returns:
        Dict with the three integer scores plus "reasoning".
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_judge_user_prompt(
                    question, context_chunks, answer, reference_answer
                ),
            },
        ],
        temperature=0.0,
        max_tokens=300,
        response_format={"type": "json_object"},
    )

    return parse_judge_response(response.choices[0].message.content)