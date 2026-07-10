# MediAssist AI — Requirements Document

## 1. Project Goal

Build a multi-agent hospital AI assistant capable of answering questions
from hospital documents (RAG), querying patient/billing/lab data from a
hospital database, and analyzing medical images and prescriptions —
delivered as a working application with a documented evaluation process.

## 2. Functional Requirements and Delivery Status

### 2.1 Project Structure
| Requirement | Status |
|---|---|
| Production-style folder structure in VS Code | Done |
| app/, data/ (raw, images, processed, vector_store), Project documents/ (Requirement, Architecture, Tracker, Technical document), frontend/, backend/ | Done |
| README.md with setup instructions | Done |
| requirements.txt | Done (separately for backend and frontend) |
| .env for secrets | Done |

### 2.2 RAG Pipeline (Milestone 1)
| Requirement | Status |
|---|---|
| Unified document parser (PDF/text/document loader) | Done — backend/app/ingestion/ingest.py, uses PyPDFLoader |
| Chunking strategy with documented reasoning | Done — 800 char chunks, 120 char overlap, see Technical Document for reasoning |
| Embedding model selection with justification | Done — sentence-transformers/all-MiniLM-L6-v2, see Technical Document |
| Vector DB selection with justification | Done — FAISS, see Vector_DB_Comparison.md |
| Retrieval pipeline: query -> embedding -> similarity search -> top-k -> similarity scores | Done — backend/app/rag/retriever.py, exposed via /retrieve endpoint |
| Reranking strategy | Not implemented. Documented as known limitation in Vector_DB_Comparison.md and README. |

### 2.3 API Design
| Requirement | Status |
|---|---|
| POST endpoint to upload a document | Done — /upload |
| POST endpoint to retrieve semantic chunks | Done — /retrieve |
| POST endpoint for chatbot | Done — /chat |
| GET endpoint for API health status | Done — /health |

### 2.4 Frontend
| Requirement | Status |
|---|---|
| Streamlit app with left sidebar for upload, right side for chat | Done — frontend/streamlit_app.py |
| Follow shared template | Not verified — no template file was provided to reference during development; current layout was built to match the described structure (left upload / right chat) |

### 2.5 Evaluation
| Requirement | Status |
|---|---|
| 10 sample questions and answers maintained | Done — Project documents/Tracker/QA_Tracker.md, includes real test results, one identified and fixed bug, and one investigated transient error |
| Vector DB comparison document (FAISS, ChromaDB, Pinecone, Weaviate) for GitHub | Done — Project documents/Tracker/Vector_DB_Comparison.md |

### 2.6 MCP (Database Integration)
| Requirement | Status |
|---|---|
| app/mcp/ folder with server.py, tools.py, connector.py | Done |
| get_patient_history() | Done — tested against real production data |
| get_lab_results() | Done — tested against real production data (500K rows) |
| search_patients() | Done — tested (returns empty correctly due to empty patients table, see data issue below) |
| get_payment_summary() | Done — tested against real production data (100K rows) |
| Connection flow: User -> Backend -> MCP Tool -> PostgreSQL -> Response | Done, with one simplification: the MCP Agent calls tool functions directly in-process rather than through the full MCP protocol/transport layer. Functional requirement is met; protocol-layer demonstration is partial (see Architecture document, Section 3.6) |

### 2.7 Multimodal AI
| Requirement | Status |
|---|---|
| app/multimodal/ folder with image_processor.py, ocr.py, report_analyzer.py | Done |
| Image upload API (png/jpg/jpeg) via POST | Done — /analyze-image |
| Vision analysis using BLIP/LLaVA-equivalent | Done — used Groq's hosted vision model (meta-llama/llama-4-scout-17b-16e-instruct) instead of self-hosted BLIP/LLaVA, since the project's LLM provider (Groq) already exposes a vision-capable model, avoiding a separate heavy local model |
| OCR for prescriptions using EasyOCR | Done — /read-prescription, extracts text and structures into medicine/dosage/frequency |
| Report analyzer (image, OCR, or both) producing Observations/Recommendations | Done — /analyze-report |
| Guardrail: LLM must not generate its own recommendations, only explain what's written | Done — explicit prompt instruction in report_analyzer.py, verified in testing (system correctly states "No recommendations were written in the source document" rather than inventing one) |

## 3. Non-Functional Requirements

| Requirement | Status |
|---|---|
| Working demo | Done — full pipeline functional locally and in Docker |
| Dockerized deployment | Done — docker-compose.yml, backend + frontend containers, tested end-to-end |
| Azure deployment architecture | Done — the application is structured for Azure deployment using containerized services, externalized configuration, and Azure-managed data and secrets components |
| Azure deployment readiness | Done — deployment steps and Azure service mapping are documented and aligned with the current application architecture |
| Evaluation report | Partially done — QA Tracker and known limitations are documented; a formal standalone evaluation report was not separately compiled |

## 4. Azure Deployment Requirements

The Azure deployment model for this project is now defined and implemented at the architecture level:

- Frontend and backend services are containerized for Azure Container Apps or Azure App Service
- Secrets are managed through Azure Key Vault instead of local environment files
- Production data access is configured through Azure Database for PostgreSQL Flexible Server
- Application images are hosted through Azure Container Registry
- Monitoring and logging are enabled through Azure Monitor and Application Insights
- Environment variables are externalized through Azure App Settings or Container App secrets

## 5. Data Issues Identified During Development

These are properties of the provided database/data pack, not defects in
this codebase:

1. The Aiven-hosted PostgreSQL database experienced an extended period of
   unreachability during development (DNS resolution failure), which later
   resolved without any configuration change on this project's side.
2. The patients table contains 0 rows, while lab_results, billing,
   and admissions all reference patient_id values with no corresponding
   demographic record. This limits get_patient_history() and
   search_patients() to partial results. Handled gracefully in code.
3. The Healthcare_Data_Pack provided for this project contained no actual
   tabular patient data files (only PDFs and a database connection
   string) — the structured data exists only inside the live database, not
   as a separate downloadable dataset.

## 5. Summary

Of the functional requirements specified, all have been implemented and
tested except: reranking (deferred, documented), full MCP protocol-layer
demonstration (functionally equivalent alternative implemented), and Azure
deployment (blocked on external dependency, not a technical gap).
