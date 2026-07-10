"""
backend/app/agents/multi_modal_agent.py

Unified wrapper matching the spec's single "multi_modal_agent.py" file.
The working implementation stays split across vision_agent.py, ocr_agent.py,
and report_analyzer_agent.py (not touched, since they're tested and
working in the graph). This file re-exports all three under one place so
the project structure matches what was asked for, without breaking the
existing wiring in graph.py.
"""

from app.agents.vision_agent import vision_node
from app.agents.ocr_agent import ocr_node
from app.agents.report_analyzer_agent import report_analyzer_node

__all__ = ["vision_node", "ocr_node", "report_analyzer_node"]


def multi_modal_node(state):
    """Convenience single entry-point: runs whichever multimodal step(s)
    the planner flagged as needed, in order (vision -> ocr -> report).
    graph.py continues to call the three nodes individually since that's
    the tested path; this function exists for spec-structure completeness
    and can be swapped in later if desired."""
    if state.get("needs_vision"):
        state = vision_node(state)
    if state.get("needs_ocr"):
        state = ocr_node(state)
    if state.get("needs_report_analysis"):
        state = report_analyzer_node(state)
    return state