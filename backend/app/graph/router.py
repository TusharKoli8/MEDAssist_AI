"""
Routing logic for the agent graph.
graph.py currently contains its own working routing functions inline (not
touched, to avoid breaking anything). This module is the canonical,
extracted version matching the required project structure — it can be
imported from graph.py in a future cleanup pass without changing behavior.
"""
 
from app.agents.state import AgentState
 
 
def next_step(state: AgentState, remaining: list) -> str:
    """Walk through a list of (step_name, flag) pairs in priority order and
    return the first step whose flag is set in the state. Falls back to
    'reasoning' if none apply."""
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
 