import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from app.agents.state import AgentState

load_dotenv()

PLANNER_PROMPT = """You are a planning agent for a hospital AI system.
The system has a document knowledge base containing hospital SOPs, compliance
policies, and any other documents staff have uploaded, AND a hospital database
with patient records, lab results, billing, and admissions data.

Given the user query, decide which of these are needed to answer it:

- mcp: needed if the question asks about a SPECIFIC patient by ID/number,
  appointment, billing, payment, lab result, or any record stored in the
  hospital database. If the question mentions a patient ID/number, a bill,
  a payment, or lab results for someone specific, this should be true and
  retrieval should usually be false.
- retrieval: needed for questions about hospital policies, SOPs, procedures,
  compliance rules, general informational/reference content found in
  uploaded documents, OR questions asking about previously uploaded or
  already-processed prescriptions/medicines when NO new image is attached
  to this specific message (e.g. "what medicines were prescribed", "what
  was in the last prescription").
- vision: needed if the question refers to an uploaded image needing general
  visual description
- ocr: needed ONLY if a NEW prescription image is attached to THIS message
  and needs to be read for the first time. If the question refers to a
  prescription from earlier in the conversation with no new image attached
  now, use retrieval instead, not ocr.
- report_analysis: needed if the question asks for a structured summary of a
  lab report or prescription image, with separate observations and
  recommendations

A question is rarely about both the document knowledge base AND the database
at the same time. Pick the one that actually matches what's being asked.

Respond ONLY with valid JSON in this exact format, no extra text:
{{"retrieval": true or false, "mcp": true or false, "vision": true or false, "ocr": true or false, "report_analysis": true or false}}

User query: {query}
"""


def planner_node(state: AgentState) -> AgentState:
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    prompt = ChatPromptTemplate.from_template(PLANNER_PROMPT)
    chain = prompt | llm

    response = chain.invoke({"query": state["user_query"]})

    try:
        decision = json.loads(response.content)
    except json.JSONDecodeError:
        # Safe fallback: if planner output is malformed, default to retrieval only
        decision = {"retrieval": True, "mcp": False, "vision": False}

    state["needs_retrieval"] = decision.get("retrieval", False)
    state["needs_mcp"] = decision.get("mcp", False)
    state["needs_vision"] = decision.get("vision", False)
    state["needs_ocr"] = decision.get("ocr", False)
    state["needs_report_analysis"] = decision.get("report_analysis", False)
    return state


if __name__ == "__main__":
    test_state: AgentState = {
        "user_query": "Show lab results for patient P1021",
        "needs_retrieval": False,
        "needs_mcp": False,
        "needs_vision": False,
        "rag_context": None,
        "rag_sources": None,
        "mcp_data": None,
        "vision_data": None,
        "final_answer": None,
    }
    result = planner_node(test_state)
    print(result)
