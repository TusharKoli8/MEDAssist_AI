"""
backend/app/logs/logger.py
 
Simple structured logging for each agent stage. Writes to separate log
files per stage (planner, rag, reason, evaluation, completed) plus console
output, so a run can be traced end-to-end after the fact.
 
Usage in any agent file:
    from app.logs.logger import log_event
    log_event("planner", {"query": query, "decision": decision})
"""
 
import os
import json
import datetime
 
LOG_DIR = os.path.join(os.path.dirname(__file__))
os.makedirs(LOG_DIR, exist_ok=True)
 
VALID_STAGES = ["planner", "rag", "mcp", "vision", "ocr", "reason", "evaluation", "completed"]
 
 
def log_event(stage: str, data: dict):
    """Append a timestamped JSON line to the log file for the given stage.
    Silently no-ops on any failure so logging never breaks the main request."""
    if stage not in VALID_STAGES:
        stage = "completed"
 
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "stage": stage,
        **data,
    }
 
    try:
        log_path = os.path.join(LOG_DIR, f"{stage}.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        print(f"[logging warning] failed to write {stage} log: {e}")
 