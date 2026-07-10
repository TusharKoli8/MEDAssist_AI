from app.agents.state import AgentState
from app.multimodal.report_analyzer import analyze_report
 
 
def report_analyzer_node(state: AgentState) -> AgentState:
    if not state.get("needs_report_analysis"):
        return state
 
    image_bytes = state.get("image_bytes")
    if not image_bytes:
        state["report_analysis_data"] = "No image was provided with this request."
        return state
 
    mime_type = state.get("image_mime_type", "image/jpeg")
    result = analyze_report(image_bytes, mime_type=mime_type, use_ocr=True)
    state["report_analysis_data"] = result
    return state
 