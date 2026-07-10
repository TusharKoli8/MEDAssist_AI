# MediAssist AI

## About

MediAssist AI is a healthcare-focused generative AI platform designed to deliver accurate, context-aware support for hospitals and clinical teams. By combining conversational intelligence, retrieval-augmented generation, multimodal analysis, and structured data access, the system helps users retrieve policies, analyze medical documents, and respond to patient-related questions with greater speed and reliability.

This capstone project demonstrates how modern AI can be applied to real-world healthcare workflows in a secure, explainable, and deployment-ready manner.

## Key Features

- Natural-language chat interface for hospital staff
- Document-based Q&A using RAG over uploaded PDFs
- Multi-agent reasoning pipeline with LangGraph
- Database-backed patient and billing queries via PostgreSQL/Aiven
- Medical image understanding for prescriptions and reports
- OCR-based prescription extraction and structuring
- Activity dashboard and usage analytics
- Docker-based deployment for easy setup and reproducibility

## System Architecture

MediAssist AI follows a layered architecture with three main components:

1. Frontend Interface
   - Built with Streamlit
   - Exposes chat, document upload, conversation history, and dashboard views
   - Runs on port 8501

2. Backend API
   - Built with FastAPI
   - Handles chat requests, document ingestion, vector retrieval, image analysis, OCR, and database tooling
   - Runs on port 8800

3. Multi-Agent Intelligence Layer
   - Implemented using LangGraph
   - Routes user requests through specialized agents such as Planner, Retriever, MCP Agent, Vision Agent, OCR Agent, Reasoning Agent, and Evaluator Agent
   - Chooses the best pathway depending on whether the user asks about documents, database records, or images

### Architecture Flow

```text
User → Streamlit Frontend → FastAPI Backend → LangGraph Agent Pipeline
                                      │
                                      ├── RAG / FAISS Document Retrieval
                                      ├── PostgreSQL / Aiven Database Queries
                                      ├── Vision and OCR Processing
                                      └── Reasoning + Evaluation
```

### Core Components

- FAISS vector store for semantic search over uploaded hospital documents
- PostgreSQL database integration for patient, lab, admission, and billing queries
- Groq LLMs for planning, reasoning, and response generation
- EasyOCR for prescription text extraction
- LangChain and LangGraph for agent orchestration

## Tech Stack

- Frontend: Streamlit
- Backend: FastAPI, Uvicorn
- Agent Orchestration: LangGraph, LangChain
- LLMs: Groq (OpenAI GPT-OSS-20B and vision-capable models)
- Vector Database: FAISS
- Embeddings: sentence-transformers / all-MiniLM-L6-v2
- OCR: EasyOCR
- Database: PostgreSQL (Aiven)
- Containerization: Docker, Docker Compose
- Environment Management: Python dotenv

## Project Structure

```text
MEDAssist_AI/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── evaluator_agent.py
│   │   │   ├── graph.py
│   │   │   ├── mcp_agent.py
│   │   │   ├── planner.py
│   │   │   ├── reasoning_agent.py
│   │   │   ├── retriever_agent.py
│   │   │   ├── vision_agent.py
│   │   │   ├── ocr_agent.py
│   │   │   ├── report_analyzer_agent.py
│   │   │   └── state.py
│   │   ├── evaluation/
│   │   │   ├── judge.py
│   │   │   ├── metrics.py
│   │   │   └── prompts.py
│   │   ├── ingestion/
│   │   │   └── ingest.py
│   │   ├── mcp/
│   │   │   ├── connector.py
│   │   │   ├── server.py
│   │   │   └── tools.py
│   │   ├── multimodal/
│   │   │   ├── image_processor.py
│   │   │   ├── ocr.py
│   │   │   └── report_analyzer.py
│   │   ├── rag/
│   │   │   └── retriever.py
│   │   ├── analytics.py
│   │   ├── config.py
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── streamlit_app.py
│   ├── Dockerfile
│   └── requirements.txt
├── data/
│   ├── images/
│   ├── raw_docs/
│   ├── processed/
│   └── vector_store/
├── Project documents/
│   ├── Architecture/
│   ├── Requirement/
│   ├── Technical document/
│   └── Tracker/
├── docker-compose.yml
├── main.py
├── pyproject.toml
├── run_app.py
└── README.md
```

## Environment Variables

Create a `.env` file in the project root with the following values:

```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=your_postgresql_connection_string_here
DATA_ROOT=./data
```

### Notes

- `GROQ_API_KEY` is required for LLM calls and vision-based analysis.
- `DATABASE_URL` connects the backend to the PostgreSQL/Aiven instance used by the MCP tools.
- `DATA_ROOT` is optional but useful for ensuring the app reads and writes data from the correct folder.

## Setup Instructions

### Option 1: Local Setup (Virtual Environment)

#### Prerequisites

- Python 3.10+
- Git
- A Groq API key
- Access to a PostgreSQL database (Aiven or local)

#### 1. Create and activate a virtual environment

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 2. Install dependencies

```bash
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

#### 3. Create the environment file

Create a `.env` file in the project root and populate it with the variables listed above.

#### 4. Build the document index (optional but recommended)

Place PDF documents inside the `data/raw_docs/` directory and run:

```bash
python backend/app/ingestion/ingest.py
```

#### 5. Run the backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8800
```

#### 6. Run the frontend

Open a second terminal and run:

```bash
streamlit run frontend/streamlit_app.py
```

The application should now be available at:

- Frontend: http://localhost:8501
- Backend API: http://localhost:8800/docs

### Option 2: Docker Compose

This project also supports containerized deployment using Docker.

#### 1. Ensure Docker Desktop is running

#### 2. Build and start the services

```bash
docker compose up --build
```

#### 3. Access the application

- Frontend: http://localhost:8501
- Backend: http://localhost:8800/docs

## API Endpoints

The FastAPI backend exposes the following routes:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/` | Backend status |
| GET | `/db-health` | Checks PostgreSQL connectivity |
| GET | `/stats` | Returns analytics and dashboard metrics |
| POST | `/upload` | Uploads a PDF and rebuilds the FAISS index |
| POST | `/retrieve` | Retrieves relevant chunks from the vector store |
| POST | `/chat` | Runs the full LangGraph multi-agent workflow |
| POST | `/analyze-image` | Performs visual analysis of an uploaded image |
| POST | `/read-prescription` | Extracts text from a prescription image and structures it |
| POST | `/analyze-report` | Summarizes lab or medical reports using OCR and vision |

## Database and MCP Integration

The system includes a custom MCP-style integration for hospital database access. The backend uses PostgreSQL queries to retrieve information about:

- patient history
- lab results
- patient search by name, city, or diagnosis
- payment and billing summaries

These capabilities are exposed through the MCP tool layer in the backend and are invoked by the LangGraph workflow when the user asks database-related questions.

## Evaluation Framework

MediAssist AI includes a dedicated evaluation layer for assessing response quality.

## Azure Deployment

MediAssist AI is planned for Azure deployment as a scalable cloud-hosted version of the capstone project. A suitable Azure architecture would include:

- Azure App Service or Azure Container Apps for the FastAPI backend
- Azure Static Web Apps or a lightweight Azure Web App for the Streamlit frontend
- Azure Database for PostgreSQL for production-grade data storage
- Azure Container Registry for container images
- Azure Key Vault for managing secrets such as `GROQ_API_KEY` and database credentials

### Recommended Azure Setup

- Backend: deploy the FastAPI service as a containerized application on Azure Container Apps or Azure App Service
- Frontend: deploy the Streamlit UI as a containerized app or static web app
- Data layer: connect the application to Azure Database for PostgreSQL instead of the local/Aiven PostgreSQL instance
- Secrets: store API keys and connection strings in Azure Key Vault and inject them as environment variables

### Azure Environment Variables

When deploying to Azure, the application should use the following environment variables:

```env
GROQ_API_KEY=your_azure_managed_secret
DATABASE_URL=your_azure_postgresql_connection_string
DATA_ROOT=/app/data
```

### Deployment Notes

- Docker images can be built locally and pushed to Azure Container Registry
- The current Docker Compose setup makes the application easy to containerize for Azure deployment
- A production deployment should also include monitoring, logging, and health checks for both services

### LLM-as-a-Judge

The evaluation framework uses an LLM-based judge to score model outputs across several dimensions:

- Faithfulness
- Grounding
- Relevance
- Completeness
- Hallucination risk

This is implemented in:

- `backend/app/evaluation/judge.py`
- `backend/app/evaluation/metrics.py`
- `backend/app/evaluation/prompts.py`

The evaluation pipeline is designed to compare responses against context, judge whether the answer is supported by evidence, and summarize performance across multiple questions.

## Usage Example

A typical interaction may include:

- asking for hospital policy information from uploaded PDFs,
- asking about patient lab results from the database,
- uploading a prescription image and asking for OCR extraction,
- analyzing a medical image or lab report visually.

## Limitations and Future Work

The current implementation already includes an Azure-ready deployment approach and a working local/containerized architecture. The next steps focus on strengthening production readiness and scaling the system further:

- improve retrieval precision with reranking and better metadata filtering
- strengthen error handling and fallback behavior for failed model calls
- expand evaluation coverage with a larger golden dataset
- refine Azure deployment operations with production monitoring, autoscaling, and secure configuration management
- improve robustness for real-world healthcare workflows and enterprise integration

## Conclusion

MediAssist AI demonstrates how modern generative AI techniques can be applied to real-world healthcare scenarios. By combining multi-agent reasoning, document retrieval, multimodal understanding, and structured database access, the system provides a strong foundation for an intelligent hospital copilot.
