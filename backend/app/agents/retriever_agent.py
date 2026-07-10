from app.agents.state import AgentState
from app.rag.retriever import load_vector_store, retrieve_context

_vector_store = None


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = load_vector_store()
    return _vector_store


def retriever_node(state: AgentState) -> AgentState:
    if not state.get("needs_retrieval"):
        return state

    vector_store = get_vector_store()
    context, sources = retrieve_context(vector_store, state["user_query"])

    state["rag_context"] = context
    state["rag_sources"] = [s.metadata.get("source", "unknown") for s in sources]
    return state


if __name__ == "__main__":
    test_state: AgentState = {
        "user_query": "What is the discharge process?",
        "needs_retrieval": True,
        "needs_mcp": False,
        "needs_vision": False,
        "rag_context": None,
        "rag_sources": None,
        "mcp_data": None,
        "vision_data": None,
        "final_answer": None,
    }
    result = retriever_node(test_state)
    print("Sources:", result["rag_sources"])
    print("\nContext snippet:\n", result["rag_context"][:300])
