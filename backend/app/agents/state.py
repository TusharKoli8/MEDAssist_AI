from typing import TypedDict, List, Optional
 
 
class AgentState(TypedDict):
    user_query: str
    needs_retrieval: bool
    needs_mcp: bool
    needs_vision: bool
    rag_context: Optional[str]
    rag_sources: Optional[List[str]]
    mcp_data: Optional[str]
    mcp_source: Optional[str]
    vision_data: Optional[str]
    image_bytes: Optional[bytes]
    image_mime_type: Optional[str]
    needs_ocr: bool
    ocr_data: Optional[dict]
    needs_report_analysis: bool
    report_analysis_data: Optional[dict]
    final_answer: Optional[str]
    evaluation: Optional[dict]
 