# MediAssist AI — Architecture Document

## 1. System Overview

MediAssist AI is a multi-agent hospital assistant. A single user query enters
through the frontend, is routed by an orchestration graph to one or more
specialized agents depending on what the query needs, and returns a single
synthesized, evaluated answer.

## 2. High-Level Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────────────────┐
│  Streamlit  │ ───► │   FastAPI    │ ───► │   LangGraph Orchestration   │
│  (frontend) │ ◄─── │   (backend)  │ ◄─── │                             │
└─────────────┘      └──────────────┘      └─────────────────────────────┘
                                                          │
                                              ┌───────────┴────────────┐
                                              │      Planner Agent     │
                                              │  (decides routing)     │
                                              └───────────┬────────────┘
                                  ┌───────────────────────┼───────────────────────┐
                                  ▼                        ▼                        ▼
                        ┌──────────────────┐   ┌──────────────────┐    ┌──────────────────┐
                        │  Retriever Agent │   │    MCP Agent     │    │   Vision/OCR      │
                        │                  │   │                  │    │   (on-demand,     │
                        │  FAISS vector    │   │  4 tool functions│    │   separate API    │
                        │  search over     │   │  -> PostgreSQL   │    │   endpoints, not  │
                        │  hospital docs   │   │  (Aiven, real    │    │   routed through  │
                        │                  │   │  production data)│    │   the main graph) │
                        └────────┬─────────┘   └────────┬─────────┘    └──────────────────┘
                                 └───────────┬───────────┘
                                             ▼
                                  ┌──────────────────────┐
                                  │   Reasoning Agent     │
                                  │  (synthesizes answer  │
                                  │   from all context)   │
                                  └──────────┬────────────┘
                                             ▼
                                  ┌──────────────────────┐
                                  │   Evaluator Agent     │
                                  │  (LLM-as-judge:        │
                                  │   grounded/relevant/   │
                                  │   safe checks)         │
                                  └──────────┬────────────┘
                                             ▼
                                       Final Answer
                                  (+ sources, + evaluation)
```

## 3. Component Breakdown

### 3.1 Frontend — Streamlit
- Two-panel layout: left sidebar for document upload, right panel for chat
- Calls backend exclusively via HTTP (`requests` library), no direct access
  to the database, vector store, or LLM
- `BACKEND_URL` configurable via environment variable for Docker networking

### 3.2 Backend — FastAPI
- Single entry point for all functionality (`backend/app/main.py`)
- Stateless request handling; the LangGraph pipeline is invoked fresh per
  `/chat` request
- Separate endpoints for direct retrieval testing (`/retrieve`), document
  upload (`/upload`), and multimodal operations (`/analyze-image`,
  `/read-prescription`, `/analyze-report`) that bypass the full agent graph
  for simpler, faster single-purpose operations

### 3.3 Orchestration — LangGraph
A `StateGraph` (`backend/app/agents/graph.py`) defines the agent flow.
Shared state (`AgentState`, a `TypedDict`) flows through every node:

```
user_query -> Planner -> [Retriever] -> [MCP] -> Reasoning -> Evaluator -> final_answer
```

Routing is conditional, not fixed:
- The Planner Agent classifies the query and sets `needs_retrieval` and
  `needs_mcp` flags via a structured LLM call
- If `needs_retrieval` is true, the graph visits the Retriever node
- After Retriever (or if retrieval wasn't needed), the graph checks
  `needs_mcp` and visits the MCP node if needed
- Both paths converge at Reasoning, then Evaluator, then end

This means a single query can use document retrieval, database lookup,
both, or neither, decided dynamically per-request rather than hardcoded.

### 3.4 Planner Agent
Single LLM call (Groq, `openai/gpt-oss-20b`) that classifies the query into
boolean flags (`retrieval`, `mcp`, `vision`) based on whether it concerns
hospital policy documents vs. patient-specific database records. The prompt
was iteratively refined during development to correctly distinguish these
two cases after early bugs caused both flags to be set simultaneously when
only one applied (see Section 5).

### 3.5 Retriever Agent
Wraps the RAG pipeline (`backend/app/rag/retriever.py`):
- Loads a pre-built FAISS index (`data/vector_store/`)
- Embeds the query using `sentence-transformers/all-MiniLM-L6-v2`
- Performs similarity search, returns top-k chunks with source document
  metadata

### 3.6 MCP Agent
Wraps 4 database tool functions (`backend/app/mcp/tools.py`):
- `get_patient_history(patient_id)`
- `get_lab_results(patient_id)`
- `search_patients(name, city, diagnosis)`
- `get_payment_summary(patient_id)`

A small LLM call interprets the natural-language query to select the
correct tool and extract parameters (e.g., patient ID) before calling the
underlying `psycopg2`-based query function against the real PostgreSQL
database. A protocol-compliant MCP server (`backend/app/mcp/server.py`,
built with FastMCP) exists matching the required project structure, but the
agent currently calls the tool functions directly in-process rather than
through the MCP transport layer — a deliberate simplification.

### 3.7 Reasoning Agent
Single LLM call that synthesizes a final natural-language answer using
whatever context is available (document chunks, database query results, or
both), explicitly instructed to use only the provided context and decline
honestly if the context doesn't answer the question.

### 3.8 Evaluator Agent
Single LLM call acting as an automated reviewer (LLM-as-judge) of the
Reasoning Agent's output, checking three criteria: grounded (no invented
facts), relevant (addresses the question), safe (no unsolicited medical
advice). Returns a structured judgment that is surfaced in the `/chat`
API response, not hidden from the caller.

### 3.9 Multimodal Components (Vision, OCR, Report Analyzer)
These are intentionally **not** part of the main LangGraph pipeline. They
are invoked through their own dedicated FastAPI endpoints
(`/analyze-image`, `/read-prescription`, `/analyze-report`), since image
upload is a fundamentally different interaction pattern than text chat.
- **Vision** (`image_processor.py`): sends the image to Groq's vision model
  with a strict observational-only prompt
- **OCR** (`ocr.py`): EasyOCR extracts raw text, then a separate LLM call
  structures it into medicine/dosage/frequency fields
- **Report Analyzer** (`report_analyzer.py`): combines vision and OCR
  outputs into an Observations/Recommendations summary, with an explicit
  instruction never to invent recommendations not present in the source

### 3.10 Data Layer
- **FAISS** (`data/vector_store/`): local file-based vector index, holds
  embeddings for 5 hospital SOP/compliance PDFs (62 chunks total)
- **PostgreSQL** (Aiven-hosted): real production-scale data —
  `lab_results` (500,000 rows), `billing` (100,000 rows), `admissions`
  (50,000 rows). Note: `patients` table is empty (0 rows) despite being
  referenced by the other tables; handled gracefully in application code
  rather than treated as a fatal error

## 4. Deployment Architecture

### 4.1 Local Docker Deployment

```
┌─────────────────────────────────────────────┐
│              Docker host                      │
│                                                │
│  ┌──────────────────┐   ┌──────────────────┐ │
│  │  frontend         │   │  backend          │ │
│  │  container        │──►│  container        │ │
│  │  (Streamlit,      │   │  (FastAPI,        │ │
│  │   port 8501)      │   │   port 8800)      │ │
│  └──────────────────┘   └────────┬──────────┘ │
│                                    │            │
└────────────────────────────────────┼────────────┘
                                     ▼
                          External PostgreSQL
                          (Aiven cloud, internet)
                                     │
                                     ▼
                          External Groq API
                          (LLM + vision, internet)
```

Both services run as separate Docker containers on a shared internal Docker
network (`docker-compose.yml`), communicating via service name
(`http://backend:8800`) rather than `localhost`. The vector store directory
is mounted as a volume (`./data:/app/data`) so the FAISS index persists and
can be rebuilt without rebuilding the image.

### 4.2 Azure Deployment Architecture

The application has been structured for Azure deployment as a cloud-hosted
version of the same architecture. The Azure deployment uses managed services
so that the application can be run securely, monitored effectively, and
scaled more easily than the local Docker setup.

```
User → Azure Container Apps / App Service (Frontend)
                 │
                 ▼
        Azure Container Apps / App Service (Backend)
                 │
        ┌────────┼───────────────┐
        ▼        ▼               ▼
 Azure DB for PostgreSQL   Azure Key Vault   Azure Container Registry
        │                        │                 │
        ▼                        ▼                 ▼
   Application Insights / Azure Monitor   Azure OpenAI / Groq API
```

Recommended Azure components:
- Frontend: Azure Container Apps or Azure App Service
- Backend: Azure Container Apps or Azure App Service
- Container images: Azure Container Registry
- Secrets and API keys: Azure Key Vault
- Data layer: Azure Database for PostgreSQL Flexible Server
- Monitoring: Azure Monitor and Application Insights
- Optional AI integration: Azure OpenAI or managed Azure AI services

Azure-specific design notes:
- Environment variables are configured as App Settings or Container App
  secrets rather than hard-coded in source files
- The backend uses managed identity where possible for secure access to
  Azure services
- The current Docker-based setup is fully compatible with Azure deployment,
  since the frontend and backend are already separated into independent
  services

## 5. Design Decisions and Trade-offs

| Decision | Reasoning |
|---|---|
| FAISS over ChromaDB/Pinecone/Weaviate | No infrastructure overhead, free, sufficient for project's data scale (<1,000 vectors). See `Vector_DB_Comparison.md` for full analysis. |
| In-process MCP tool calls instead of full MCP protocol transport | Avoids adding a separate MCP client/transport layer for a single-process application; functional requirement (4 working DB tools) is satisfied without the added complexity. |
| Separate endpoints for multimodal instead of routing through the main graph | Image upload is a different interaction shape than text chat; keeping it as direct endpoints keeps both paths simpler and avoids forcing image handling through state designed for text. |
| Evaluator output returned to the caller instead of hidden | Makes the system's self-assessment visible and auditable, supporting the project's evaluation/tracker requirements rather than treating evaluation as an internal-only safety net. |
| No reranking (yet) | Deferred due to added complexity and the project's current data scale not yet requiring it; documented as a known limitation with a clear upgrade path. |

## 6. Known Architectural Gaps

- No reranking or metadata filtering in the retrieval layer
- MCP server exists but the protocol/transport layer is not exercised by
  the live agent path
- No persistent conversation memory across `/chat` requests (each request
  is stateless)
- No authentication/authorization layer (out of scope for this capstone,
  but would be required before any real deployment with real patient data)
