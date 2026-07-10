import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.agents.mcp_agent import mcp_node
from app.agents.state import AgentState
from app.agents.planner import planner_node
from app.agents.retriever_agent import retriever_node
from app.agents.reasoning_agent import reasoning_node
from app.agents.evaluator_agent import evaluator_node
from app.agents.vision_agent import vision_node
from app.agents.ocr_agent import ocr_node
from app.agents.report_analyzer_agent import report_analyzer_node

load_dotenv()


def next_step(state: AgentState, remaining: list) -> str:
    for step_name, flag in remaining:
        if state.get(flag):
            return step_name
    return "reasoning"


def route_after_planner(state: AgentState) -> str:
    return next_step(state, [
        ("retriever", "needs_retrieval"),
        ("mcp", "needs_mcp"),
        ("vision", "needs_vision"),
        ("ocr", "needs_ocr"),
        ("report_analysis", "needs_report_analysis"),
    ])


def route_after_retriever(state: AgentState) -> str:
    return next_step(state, [
        ("mcp", "needs_mcp"),
        ("vision", "needs_vision"),
        ("ocr", "needs_ocr"),
        ("report_analysis", "needs_report_analysis"),
    ])


def route_after_mcp(state: AgentState) -> str:
    return next_step(state, [
        ("vision", "needs_vision"),
        ("ocr", "needs_ocr"),
        ("report_analysis", "needs_report_analysis"),
    ])


def route_after_vision(state: AgentState) -> str:
    return next_step(state, [
        ("ocr", "needs_ocr"),
        ("report_analysis", "needs_report_analysis"),
    ])


def route_after_ocr(state: AgentState) -> str:
    return next_step(state, [
        ("report_analysis", "needs_report_analysis"),
    ])


ALL_TARGETS = {
    "retriever": "retriever",
    "mcp": "mcp",
    "vision": "vision",
    "ocr": "ocr",
    "report_analysis": "report_analysis",
    "reasoning": "reasoning",
}


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("mcp", mcp_node)
    graph.add_node("vision", vision_node)
    graph.add_node("ocr", ocr_node)
    graph.add_node("report_analysis", report_analyzer_node)
    graph.add_node("reasoning", reasoning_node)
    graph.add_node("evaluator", evaluator_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges("planner", route_after_planner, ALL_TARGETS)
    graph.add_conditional_edges("retriever", route_after_retriever, ALL_TARGETS)
    graph.add_conditional_edges("mcp", route_after_mcp, ALL_TARGETS)
    graph.add_conditional_edges("vision", route_after_vision, ALL_TARGETS)
    graph.add_conditional_edges("ocr", route_after_ocr, ALL_TARGETS)
    graph.add_edge("report_analysis", "reasoning")
    graph.add_edge("reasoning", "evaluator")
    graph.add_edge("evaluator", END)

    return graph.compile()


if __name__ == "__main__":
    app_graph = build_graph()

    test_state: AgentState = {
        "user_query": "What is the discharge process?",
        "needs_retrieval": False,
        "needs_mcp": False,
        "needs_vision": False,
        "needs_ocr": False,
        "needs_report_analysis": False,
        "rag_context": None,
        "rag_sources": None,
        "mcp_data": None,
        "vision_data": None,
        "ocr_data": None,
        "report_analysis_data": None,
        "image_bytes": None,
        "image_mime_type": None,
        "final_answer": None,
        "evaluation": None,
    }

    result = app_graph.invoke(test_state)
    print("Query:", result["user_query"])
    print("\nFinal Answer:\n", result["final_answer"])
    print("\nSources:", result.get("rag_sources"))