import sys
import asyncio
 
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
 
from streamlit.web import cli as stcli
 
if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        "frontend/streamlit_app.py",
        "--server.fileWatcherType",
        "none",
    ]
    sys.exit(stcli.main())
 