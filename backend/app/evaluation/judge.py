"""
backend/app/evaluation/judge.py
 
LLM-as-a-judge: scores a question/context/answer triple across multiple
metrics (1-10 scale each, with a reason), independent of the inline
grounded/relevant/safe check already done by evaluator_agent.py.
This is the deeper scoring layer used for the golden-dataset evaluation
framework, not the per-request quality gate.
"""
 
import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from app.evaluation.prompts import JUDGE_PROMPT

load_dotenv()
 
 
def judge_answer(question: str, context: str, answer: str) -> dict:
    """Returns a dict of metric -> {score, reason}, using an LLM judge."""
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    prompt = JUDGE_PROMPT.format(question=question, context=context, answer=answer)
 
    response = llm.invoke(prompt)
    raw = response.content.strip()
 
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "faithfulness": {"score": None, "reason": "judge output could not be parsed"},
            "grounding": {"score": None, "reason": "judge output could not be parsed"},
            "relevance": {"score": None, "reason": "judge output could not be parsed"},
            "completeness": {"score": None, "reason": "judge output could not be parsed"},
            "hallucination_risk": {"score": None, "reason": "judge output could not be parsed"},
            "raw_output": raw,
        }
    return result
 