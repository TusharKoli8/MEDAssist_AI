from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
 
from app.agents.state import AgentState
 
load_dotenv()
 
REASONING_PROMPT = """You are the reasoning component of a hospital AI assistant.
Synthesize a clear, direct answer to the user's question using ONLY the context
provided below. Do not use outside medical knowledge. If the context does not
answer the question, say so honestly instead of guessing.

Document context (from hospital SOPs/policies):
{rag_context}

Database context (patient/appointment/billing data):
{mcp_context}

Image/vision context:
{vision_context}

OCR/prescription context:
{ocr_context}

Report analysis context:
{report_context}

Question:
{question}

Answer:"""
 
 
def reasoning_node(state: AgentState) -> AgentState:
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    prompt = ChatPromptTemplate.from_template(REASONING_PROMPT)
    chain = prompt | llm
 
    response = chain.invoke({
        "rag_context": state.get("rag_context") or "Not available.",
        "mcp_context": state.get("mcp_data") or "Not available.",
        "vision_context": state.get("vision_data") or "Not available.",
        "ocr_context": state.get("ocr_data") or "Not available.",
        "report_context": state.get("report_analysis_data") or "Not available.",
        "question": state["user_query"],
    })
 
    state["final_answer"] = response.content
    return state
 