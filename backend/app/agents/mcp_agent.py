import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
 
from app.agents.state import AgentState
from app.mcp.tools import (
    get_patient_history,
    get_lab_results,
    search_patients,
    get_payment_summary,
)
 
load_dotenv()
 
TOOL_SELECTION_PROMPT = """You are selecting a database tool to answer a hospital
staff question.
 
Available tools:
- patient_history: needs patient_id (integer). Returns admissions and demographics.
- lab_results: needs patient_id (integer). Returns recent lab test results.
- payment_summary: needs patient_id (integer). Returns billing information.
- patient_search: needs any of name, city, diagnosis (strings). Searches for patients.
 
Extract the patient_id if a number is mentioned in the query. If no patient_id is
mentioned and the query seems to be a search (by name/city/diagnosis), use
patient_search instead.
 
Respond ONLY with valid JSON in this format:
{{"tool": "tool_name", "patient_id": integer or null, "name": "..." or null, "city": "..." or null, "diagnosis": "..." or null}}
 
User query: {query}
"""
 
 
def mcp_node(state: AgentState) -> AgentState:
    if not state.get("needs_mcp"):
        return state
 
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    prompt = ChatPromptTemplate.from_template(TOOL_SELECTION_PROMPT)
    chain = prompt | llm
 
    response = chain.invoke({"query": state["user_query"]})
 
    try:
        decision = json.loads(response.content)
    except json.JSONDecodeError:
        state["mcp_data"] = "Could not determine which database tool to use for this query."
        return state
 
    tool = decision.get("tool")
    patient_id = decision.get("patient_id")
 
    try:
        if tool == "patient_history" and patient_id:
            result = get_patient_history(patient_id)
        elif tool == "lab_results" and patient_id:
            result = get_lab_results(patient_id)
        elif tool == "payment_summary" and patient_id:
            result = get_payment_summary(patient_id)
        elif tool == "patient_search":
            result = search_patients(
                name=decision.get("name"),
                city=decision.get("city"),
                diagnosis=decision.get("diagnosis"),
            )
        else:
            result = {"message": "Could not identify a patient ID or search term in the query."}
    except Exception as e:
        result = {"error": f"Database query failed: {str(e)}"}
 
    state["mcp_data"] = json.dumps(result, default=str)
    state["mcp_source"] = f"PostgreSQL database (tool: {tool}, patient_id: {patient_id})"
    return state