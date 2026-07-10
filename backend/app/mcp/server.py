from mcp.server.fastmcp import FastMCP
 
from app.mcp.tools import (
    get_patient_history,
    get_lab_results,
    search_patients,
    get_payment_summary,
)
 
mcp = FastMCP("MediAssist-DB")
 
 
@mcp.tool()
def patient_history(patient_id: int) -> dict:
    """Get a patient's admission history and basic demographic record."""
    return get_patient_history(patient_id)
 
 
@mcp.tool()
def lab_results(patient_id: int, limit: int = 10) -> dict:
    """Get recent lab results for a patient."""
    return get_lab_results(patient_id, limit)
 
 
@mcp.tool()
def patient_search(name: str = None, city: str = None, diagnosis: str = None) -> dict:
    """Search patients by name, city, or diagnosis."""
    return search_patients(name, city, diagnosis)
 
 
@mcp.tool()
def payment_summary(patient_id: int) -> dict:
    """Get billing and payment summary for a patient."""
    return get_payment_summary(patient_id)
 
 
if __name__ == "__main__":
    mcp.run()
 