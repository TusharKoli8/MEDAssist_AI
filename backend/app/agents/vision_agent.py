from app.agents.state import AgentState
from app.multimodal.image_processor import analyze_image


def vision_node(state: AgentState) -> AgentState:
    if not state.get("needs_vision"):
        return state

    image_bytes = state.get("image_bytes")
    if not image_bytes:
        state["vision_data"] = "No image was provided with this request."
        return state

    mime_type = state.get("image_mime_type", "image/jpeg")
    result = analyze_image(image_bytes, mime_type=mime_type)
    state["vision_data"] = result
    return state