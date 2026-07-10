"""
backend/app/evaluation/prompts.py

Prompt template for the LLM-as-judge scoring used by judge.py, applied
across the golden dataset for the full evaluation framework (separate
from the lightweight per-request grounded/relevant/safe check in
evaluator_agent.py).
"""

JUDGE_PROMPT = """You are an AI evaluator for a hospital assistant system.
Given the question, the context that was available to the answering model,
and the answer it produced, score the answer on the following metrics.
Return a score from 1 to 10 for each metric, with a short reason.

Metrics:
- faithfulness: does the answer only state things supported by the context, without adding unsupported claims?
- grounding: is every factual claim in the answer traceable to the given context?
- relevance: does the answer actually address what was asked?
- completeness: does the answer cover the key relevant points available in the context?
- hallucination_risk: 10 = no hallucination detected, 1 = answer is substantially fabricated.

Question:
{question}

Context:
{context}

Answer:
{answer}

Respond ONLY with valid JSON in this exact format, no extra text:
{{
  "faithfulness": {{"score": <1-10>, "reason": "..."}},
  "grounding": {{"score": <1-10>, "reason": "..."}},
  "relevance": {{"score": <1-10>, "reason": "..."}},
  "completeness": {{"score": <1-10>, "reason": "..."}},
  "hallucination_risk": {{"score": <1-10>, "reason": "..."}}
}}
"""