import uuid
from app.agents.state import AgentState
from app.multimodal.ocr import process_prescription
from app.ingestion.ingest import add_to_vector_store


def ocr_node(state: AgentState) -> AgentState:
    if not state.get("needs_ocr"):
        return state

    image_bytes = state.get("image_bytes")
    if not image_bytes:
        state["ocr_data"] = "No image was provided with this request."
        return state

    result = process_prescription(image_bytes)
    state["ocr_data"] = result

    raw_text = result.get("raw_ocr_text", "")
    if raw_text.strip():
        try:
            add_to_vector_store(
                text=raw_text,
                metadata={
                    "source": f"prescription_{uuid.uuid4().hex[:8]}",
                    "doc_type": "prescription",
                },
            )
        except Exception as e:
            print(f"Warning: failed to store prescription text: {e}")

    return state
 