from app.mcp.connector import run_query
 
 
def get_patient_history(patient_id: int) -> dict:
    """Returns admissions, diagnosis, and basic record for a patient."""
    patient_record = run_query(
        "SELECT * FROM patients WHERE patient_id = %s;", (patient_id,)
    )
 
    admissions = run_query(
        """SELECT admission_id, admission_reason, ward, admitted_on, discharged_on
           FROM admissions WHERE patient_id = %s
           ORDER BY admitted_on DESC;""",
        (patient_id,),
    )
 
    if not patient_record and not admissions:
        return {
            "patient_id": patient_id,
            "found": False,
            "message": "No record found for this patient ID.",
        }
 
    return {
        "patient_id": patient_id,
        "found": True,
        "demographics": patient_record[0] if patient_record else None,
        "demographics_note": None if patient_record else "No demographic record found for this patient_id, though related records exist.",
        "admissions": admissions,
    }
 
 
def get_lab_results(patient_id: int, limit: int = 10) -> dict:
    """Returns recent lab results for a patient."""
    results = run_query(
        """SELECT lab_id, test_name, result, report_date
           FROM lab_results WHERE patient_id = %s
           ORDER BY report_date DESC
           LIMIT %s;""",
        (patient_id, limit),
    )
 
    return {
        "patient_id": patient_id,
        "found": len(results) > 0,
        "results": results,
    }
 
 
def search_patients(name: str = None, city: str = None, diagnosis: str = None) -> dict:
    """Searches the patients table by partial name, city, or diagnosis match.
    Note: patients table may be empty in current data; this will return no
    matches in that case even if related records exist elsewhere."""
    conditions = []
    params = []
 
    if name:
        conditions.append("patient_name ILIKE %s")
        params.append(f"%{name}%")
    if city:
        conditions.append("city ILIKE %s")
        params.append(f"%{city}%")
    if diagnosis:
        conditions.append("diagnosis ILIKE %s")
        params.append(f"%{diagnosis}%")
 
    if not conditions:
        return {"found": False, "message": "Provide at least one search field: name, city, or diagnosis."}
 
    query = f"SELECT * FROM patients WHERE {' AND '.join(conditions)} LIMIT 20;"
    results = run_query(query, tuple(params))
 
    return {
        "found": len(results) > 0,
        "count": len(results),
        "results": results,
    }
 
 
def get_payment_summary(patient_id: int) -> dict:
    """Returns billing summary for a patient."""
    bills = run_query(
        """SELECT bill_id, amount, insurance_provider, payment_status
           FROM billing WHERE patient_id = %s;""",
        (patient_id,),
    )
 
    if not bills:
        return {
            "patient_id": patient_id,
            "found": False,
            "message": "No billing records found for this patient ID.",
        }
 
    total_amount = sum(float(b["amount"]) for b in bills)
 
    return {
        "patient_id": patient_id,
        "found": True,
        "total_billed": total_amount,
        "bill_count": len(bills),
        "bills": bills,
    }
 