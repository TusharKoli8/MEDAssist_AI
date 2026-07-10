 
import os
import json
import datetime
 
DATA_DIR = os.environ.get("DATA_ROOT")
if not DATA_DIR:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
 
LOG_PATH = os.path.join(DATA_DIR, "activity_log.json")
 
 
def _load_log() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []
 
 
def _save_log(events: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, default=str)
 
 
def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 characters per token. Not exact billed tokens."""
    if not text:
        return 0
    return max(1, len(text) // 4)
 
 
def log_activity(event_type: str, detail: dict = None, response_time: float = None,
                  tokens_estimate: int = None):
    """Append one event to the activity log. Never raises — a logging
    failure should never break the actual request."""
    try:
        events = _load_log()
        events.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "event_type": event_type,
            "detail": detail or {},
            "response_time": response_time,
            "tokens_estimate": tokens_estimate,
        })
        # Keep the log from growing unbounded — cap at last 2000 events
        events = events[-2000:]
        _save_log(events)
    except Exception as e:
        print(f"[analytics warning] failed to log activity: {e}")
 
 
def get_stats() -> dict:
    """Aggregate the raw event log into dashboard-ready statistics.
 
    NOTE: the frontend routes ALL activity (including image/prescription/
    report uploads attached to a question) through POST /chat — it never
    calls the standalone /analyze-image, /read-prescription, or
    /analyze-report endpoints. Those endpoints tag their own event_type
    directly, but /chat instead tags a single "chat" event with an
    `agent_path` detail field ("vision", "ocr", "report_analysis", etc).
    So the counts below check BOTH: the dedicated event_type (in case
    those endpoints are ever called directly, e.g. by another client)
    AND the agent_path recorded on ordinary "chat" events (the path
    actually used today by the Streamlit frontend). Without the second
    check, these counters stay at 0 forever even with heavy real usage.
    """
    events = _load_log()
 
    def is_chat_with_path(e, path):
        return e["event_type"] == "chat" and e["detail"].get("agent_path") == path
 
    total_questions = sum(1 for e in events if e["event_type"] == "chat")
    total_uploads = sum(1 for e in events if e["event_type"] == "upload")
 
    total_images = sum(
        1 for e in events
        if e["event_type"] == "analyze_image" or is_chat_with_path(e, "vision")
    )
    total_prescriptions = sum(
        1 for e in events
        if e["event_type"] == "read_prescription" or is_chat_with_path(e, "ocr")
    )
    total_reports = sum(
        1 for e in events
        if e["event_type"] == "analyze_report" or is_chat_with_path(e, "report_analysis")
    )
 
    total_errors = sum(1 for e in events if e["detail"].get("error"))
 
    total_tokens = sum(e.get("tokens_estimate") or 0 for e in events)
 
    response_times = [e["response_time"] for e in events if e.get("response_time")]
    avg_response_time = round(sum(response_times) / len(response_times), 2) if response_times else 0
 
    agent_path_counts = {}
    for e in events:
        if e["event_type"] == "chat":
            path = e["detail"].get("agent_path", "unknown")
            agent_path_counts[path] = agent_path_counts.get(path, 0) + 1
 
    # Activity per day (last 14 days that have data)
    per_day = {}
    for e in events:
        day = e["timestamp"][:10]
        per_day[day] = per_day.get(day, 0) + 1
    per_day_sorted = dict(sorted(per_day.items())[-14:])
 
    recent_activity = list(reversed(events[-15:]))
 
    return {
        "total_questions": total_questions,
        "total_uploads": total_uploads,
        "total_images_analyzed": total_images,
        "total_prescriptions_read": total_prescriptions,
        "total_reports_analyzed": total_reports,
        "total_errors": total_errors,
        "total_tokens_estimate": total_tokens,
        "avg_response_time_sec": avg_response_time,
        "agent_path_counts": agent_path_counts,
        "activity_per_day": per_day_sorted,
        "recent_activity": recent_activity,
        "total_events_logged": len(events),
    }
 