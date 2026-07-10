import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
 
import os
import json
import uuid
import base64
from datetime import datetime
 
import streamlit as st
import requests
import pandas as pd
 
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8800")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "chat_history.json")
MAX_QUESTIONS_PER_CHAT = 10


def render_dashboard():
    st.title("Activity Dashboard")
    st.caption("Live usage stats for MediAssist AI")
    try:
        response = requests.get(f"{BACKEND_URL}/stats", timeout=10)
        response.raise_for_status()
        stats = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Could not load dashboard stats: {e}")
        return
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Questions Asked", stats.get("total_questions", 0))
    col2.metric("Documents Uploaded", stats.get("total_uploads", 0))
    col3.metric("Images Analyzed", stats.get("total_images_analyzed", 0))
    col4.metric("Prescriptions Read", stats.get("total_prescriptions_read", 0))
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Reports Analyzed", stats.get("total_reports_analyzed", 0))
    col6.metric("Errors Logged", stats.get("total_errors", 0))
    col7.metric("Avg Response Time", f"{stats.get('avg_response_time_sec', 0)}s")
    col8.metric("Tokens Used (est.)", f"{stats.get('total_tokens_estimate', 0):,}")
    st.caption(
        "Token count is an estimate (~4 characters per token), not exact "
        "billed usage — Groq's API response doesn't currently expose "
        "precise token counts in this integration."
    )
    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("Which Agent Answered")
        agent_counts = stats.get("agent_path_counts", {})
        if agent_counts:
            df = pd.DataFrame(
                {"Agent": list(agent_counts.keys()), "Questions": list(agent_counts.values())}
            ).set_index("Agent")
            st.bar_chart(df)
        else:
            st.write("No chat activity yet.")
    with right:
        st.subheader("Activity Over Time")
        per_day = stats.get("activity_per_day", {})
        if per_day:
            df = pd.DataFrame(
                {"Date": list(per_day.keys()), "Events": list(per_day.values())}
            ).set_index("Date")
            st.line_chart(df)
        else:
            st.write("No activity history yet.")
    st.divider()
    st.subheader("Recent Activity")
    recent = stats.get("recent_activity", [])
    if recent:
        rows = []
        for e in recent:
            detail = e.get("detail", {})
            summary = (
                detail.get("query") or detail.get("filename") or
                detail.get("medicines_found") or "-"
            )
            rows.append({
                "Time": e["timestamp"].replace("T", " ")[:19],
                "Type": e["event_type"],
                "Detail": str(summary)[:80],
                "Response Time (s)": e.get("response_time", "-"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.write("Nothing logged yet — ask a question or upload a document to see activity here.")
    st.caption(f"Total events logged: {stats.get('total_events_logged', 0)}")

 
st.set_page_config(page_title="MediAssist AI", page_icon=None, layout="wide")
mode = st.sidebar.radio("View", ["Chat", "Dashboard"], horizontal=True)
 
 
# ---------- Persistence helpers ----------
def load_all_conversations():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
 
 
def save_all_conversations(conversations):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(conversations, f, indent=2)
 
 
def new_conversation_id():
    return uuid.uuid4().hex[:8]
 
 
def conversation_title(messages):
    for m in messages:
        if m["role"] == "user":
            text = m["content"].strip()
            return text[:40] + ("..." if len(text) > 40 else "")
    return "New chat"
 
 
# ---------- Session state init ----------
if "conversations" not in st.session_state:
    st.session_state.conversations = load_all_conversations()
 
if "current_chat_id" not in st.session_state:
    if st.session_state.conversations:
        latest_id = max(
            st.session_state.conversations,
            key=lambda cid: st.session_state.conversations[cid].get("updated_at", ""),
        )
        st.session_state.current_chat_id = latest_id
    else:
        new_id = new_conversation_id()
        st.session_state.conversations[new_id] = {
            "messages": [],
            "updated_at": datetime.now().isoformat(),
        }
        st.session_state.current_chat_id = new_id
 
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = None
 
if "selected_stored_image" not in st.session_state:
    st.session_state.selected_stored_image = None
 
 
def get_current_messages():
    return st.session_state.conversations[st.session_state.current_chat_id]["messages"]
 
 
def count_user_questions(messages):
    return sum(1 for m in messages if m["role"] == "user")
 
 
def start_new_conversation():
    new_id = new_conversation_id()
    st.session_state.conversations[new_id] = {
        "messages": [],
        "updated_at": datetime.now().isoformat(),
    }
    st.session_state.current_chat_id = new_id
    save_all_conversations(st.session_state.conversations)
 
 
def delete_conversation(cid):
    if cid in st.session_state.conversations:
        del st.session_state.conversations[cid]
        save_all_conversations(st.session_state.conversations)
        if st.session_state.current_chat_id == cid:
            if st.session_state.conversations:
                st.session_state.current_chat_id = max(
                    st.session_state.conversations,
                    key=lambda c: st.session_state.conversations[c].get("updated_at", ""),
                )
            else:
                start_new_conversation()
    st.session_state.confirm_delete = None
 
 
if mode == "Chat":
    # ---------- LEFT SIDEBAR ----------
    with st.sidebar:
        # Upload Documents — exactly as original
        st.header("Upload Documents")
        uploaded_files = st.file_uploader("Choose PDF files", type=["pdf"], accept_multiple_files=True)
 
        if uploaded_files:
            if st.button("Upload and Index"):
                for uploaded_file in uploaded_files:
                    with st.spinner(f"Uploading {uploaded_file.name}..."):
                        try:
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                            response = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=120)
                            response.raise_for_status()
                            data = response.json()
                            st.success(f"Indexed: {data.get('filename')}")
                        except requests.exceptions.RequestException as e:
                            st.error(f"Upload failed: {uploaded_file.name} — {e}")
 
        st.divider()
        st.caption("Backend status")
        try:
            health = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if health.status_code == 200:
                st.success("Backend connected")
            else:
                st.warning("Backend responded with an error")
        except requests.exceptions.RequestException:
            st.error("Backend not reachable")
 
        st.caption("Database status")
        try:
            db_health = requests.get(f"{BACKEND_URL}/db-health", timeout=15)
            db_data = db_health.json()
            if db_data.get("status") == "ok":
                st.success("Database connected")
            else:
                st.error(f"Database error: {db_data.get('detail', 'unknown')}")
        except requests.exceptions.RequestException as e:
            st.error(f"Database not reachable: {e}")
 
        st.divider()
        st.header("Chat History")
 
        if st.button("+ New chat", use_container_width=True):
            start_new_conversation()
            st.rerun()
 
        sorted_chat_ids = sorted(
            st.session_state.conversations,
            key=lambda cid: st.session_state.conversations[cid].get("updated_at", ""),
            reverse=True,
        )
 
        for cid in sorted_chat_ids:
            convo = st.session_state.conversations[cid]
            title = conversation_title(convo["messages"])
            is_current = cid == st.session_state.current_chat_id
            label = ("> " if is_current else "") + title
 
            col1, col2 = st.columns([5, 1])
 
            with col1:
                if st.button(label, key=f"convo_btn_{cid}", use_container_width=True):
                    st.session_state.current_chat_id = cid
                    st.session_state.confirm_delete = None
                    st.rerun()
 
            with col2:
                if st.button("🗑", key=f"del_btn_{cid}", help="Delete"):
                    st.session_state.confirm_delete = cid
                    st.rerun()
 
            if st.session_state.confirm_delete == cid:
                st.warning("Delete this chat?")
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("Yes", key=f"confirm_yes_{cid}", use_container_width=True):
                        delete_conversation(cid)
                        st.rerun()
                with dc2:
                    if st.button("No", key=f"confirm_no_{cid}", use_container_width=True):
                        st.session_state.confirm_delete = None
                        st.rerun()
 
 
    # ---------- RIGHT PANEL: Chat ----------
    st.title("MediAssist AI")
    st.caption("Hospital knowledge assistant")
 
    current_messages = get_current_messages()
    question_count = count_user_questions(current_messages)
 
    if question_count >= MAX_QUESTIONS_PER_CHAT:
        st.warning(
            f"This chat has reached the {MAX_QUESTIONS_PER_CHAT} question limit. "
            "You can still read this chat. Click '+ New chat' in the sidebar to continue."
        )
 
    # Render existing messages
    for message in current_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("image_bytes"):
                img_bytes = base64.b64decode(message["image_bytes"])
                st.image(img_bytes, width=200, caption=message.get("image_name", "Attached image"))
            if message.get("sources"):
                unique_sources = sorted(set(message["sources"]))
                st.caption("Sources: " + ", ".join(unique_sources))
 
    chat_image = st.file_uploader(
        "Attach an image (optional, for vision/OCR questions)",
        key=f"chat_image_uploader_{len(current_messages)}_{st.session_state.current_chat_id}",
        type=["png", "jpg", "jpeg"],
    )

    if question_count >= MAX_QUESTIONS_PER_CHAT:
        user_input = None
        st.chat_input("Limit reached — start a new chat from the sidebar", disabled=True)
    else:
        user_input = st.chat_input(
            f"Ask a question... ({question_count}/{MAX_QUESTIONS_PER_CHAT} used)"
        )
 
    if user_input:
        image_b64 = None
        image_name = None
 
        if chat_image is not None:
            # Priority 1 — fresh image uploaded this turn
            image_b64 = base64.b64encode(chat_image.getvalue()).decode("utf-8")
            image_name = chat_image.name
 
        elif st.session_state.selected_stored_image:
            # Priority 2 — stored image selected from sidebar buttons
            # Only send if question is image-related AND not a database/patient query
            image_keywords = ["image", "photo", "picture", "uploaded", "shared", "show",
                              "skin", "prescription", "describe", "define",
                              "what is in", "what does", "read", "extract", "medicine",
                              "diagnos", "lesion", "disease", "hand", "report",
                              "tell me about the image", "what does the image",
                              "smth about the image"]
            db_keywords = ["patient id", "patient ID", "for patient",
                           "blood test reports for", "lab results for",
                           "billing for", "search for patient", "show me patient"]
            query_lower = user_input.lower()
            is_image_question = any(kw in query_lower for kw in image_keywords)
            is_db_question = any(kw in query_lower for kw in db_keywords)
            if is_image_question and not is_db_question:
                try:
                    img_url = f"{BACKEND_URL}/images/{st.session_state.selected_stored_image}"
                    img_r = requests.get(img_url, timeout=10)
                    img_r.raise_for_status()
                    image_b64 = base64.b64encode(img_r.content).decode("utf-8")
                    image_name = st.session_state.selected_stored_image
                except requests.exceptions.RequestException:
                    st.warning("Could not load stored image — attach it manually.")
 
        else:
            # Priority 3 — look back in chat history for last attached image
            image_keywords = ["image", "photo", "picture", "uploaded", "shared", "show",
                              "skin", "prescription", "describe", "define",
                              "what is in", "what does", "medicine", "diagnos",
                              "lesion", "disease", "hand", "report"]
            db_keywords = ["patient id", "patient ID", "for patient",
                           "blood test reports for", "lab results for",
                           "billing for", "search for patient", "show me patient"]
            query_lower = user_input.lower()
            is_image_question = any(kw in query_lower for kw in image_keywords)
            is_db_question = any(kw in query_lower for kw in db_keywords)
            if is_image_question and not is_db_question:
                for msg in reversed(current_messages):
                    if msg["role"] == "user" and msg.get("image_bytes"):
                        image_b64 = msg["image_bytes"]
                        image_name = msg.get("image_name", "image.jpg")
                        break
 
        user_msg = {"role": "user", "content": user_input}
        if image_b64:
            user_msg["image_bytes"] = image_b64
            user_msg["image_name"] = image_name
        current_messages.append(user_msg)
 
        with st.chat_message("user"):
            st.write(user_input)
            if chat_image:
                st.image(chat_image, width=200)
 
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    files = {}
                    if chat_image is not None:
                        files["image"] = (chat_image.name, chat_image.getvalue(), chat_image.type)
                    elif image_b64 and image_name:
                        img_type = "image/jpeg" if image_name.lower().endswith((".jpg", ".jpeg")) else "image/png"
                        files["image"] = (image_name, base64.b64decode(image_b64), img_type)
 
                    response = requests.post(
                        f"{BACKEND_URL}/chat",
                        data={"query": user_input},
                        files=files if files else None,
                        timeout=60,
                    )
                    response.raise_for_status()
                    data = response.json()
                    answer = data.get("answer", "No answer received.")
                    sources = data.get("sources", [])
 
                    st.write(answer)
 
                    if sources:
                        unique_sources = sorted(set(sources))
                    elif image_b64:
                        unique_sources = [image_name] if image_name else ["Attached image"]
                    else:
                        unique_sources = []
 
                    if unique_sources:
                        st.caption("Sources: " + ", ".join(unique_sources))
 
                    current_messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": unique_sources,
                    })
 
                except requests.exceptions.RequestException as e:
                    error_msg = f"Could not reach backend: {e}"
                    st.error(error_msg)
                    current_messages.append({"role": "assistant", "content": error_msg})
 
        st.session_state.conversations[st.session_state.current_chat_id]["updated_at"] = (
            datetime.now().isoformat()
        )
        save_all_conversations(st.session_state.conversations)
        st.rerun()
else:
    render_dashboard()