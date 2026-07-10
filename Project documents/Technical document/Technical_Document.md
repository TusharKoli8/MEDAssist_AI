# MediAssist AI — Technical Document

## 1. Document Parsing

backend/app/ingestion/ingest.py uses LangChain's PyPDFLoader to load PDF
files page by page, attaching the source filename as metadata on each page
so retrieved chunks can always be traced back to their origin document.
PDF was the only format needed since all provided source material
(hospital SOPs, compliance documents) was supplied as PDF.

## 2. Chunking Strategy

Configuration: RecursiveCharacterTextSplitter, chunk size 800
characters, overlap 120 characters.

Why chunking is needed: Embedding models and LLM context windows have
practical limits, and retrieval precision degrades if a single chunk
contains multiple unrelated topics (a 13-page compliance PDF as one chunk
would return the same noisy block regardless of which specific question was
asked). Splitting into smaller, semantically focused units lets the
retriever return only the passage that's actually relevant to a given
query.

Why 800 characters: This is roughly 2-3 paragraphs of typical SOP/policy
text — large enough to preserve enough surrounding context for a
self-contained answer (e.g., a full numbered procedure step with its
sub-points), but small enough that a single chunk rarely mixes two unrelated
topics. Hospital SOP documents in this project tend to organize information
in short numbered sections, which made 800 characters a reasonable match to
the documents' natural structure (verified empirically: 5 source PDFs
totaling 59 pages produced 62 chunks, an average of roughly one chunk per
page, which matched expectations for this document style).

Why 120 character overlap: Without overlap, a sentence or list item that
spans a chunk boundary gets split mid-thought, and neither resulting chunk
contains the complete idea. A 15% overlap (120 of 800 characters) is enough
to usually capture a full sentence or short list item that straddles a
boundary, without meaningfully increasing the total number of chunks or
introducing significant duplicate content into the vector store.

Trade-off: Larger chunks reduce the risk of splitting ideas mid-thought
but increase the chance of mixing unrelated content in one chunk (diluting
relevance). Smaller chunks improve topic focus but risk losing necessary
context. The 800/120 configuration was chosen as a reasonable default for
this document style rather than tuned through systematic experimentation,
given the project's time constraints; it could be revisited with a labeled
retrieval-quality evaluation set if pursued further.

## 3. Embedding Model

Chosen model: sentence-transformers/all-MiniLM-L6-v2

Why this model:
- Runs locally via sentence-transformers/langchain-huggingface, with no
  external API call needed for embedding (only generation calls go to
  Groq), reducing cost and latency for the ingestion and retrieval steps
- Small (~90MB), fast to load and run on CPU, appropriate for this
  project's scale (62 chunks) and the lack of GPU infrastructure in the
  development and deployment environment
- Well-established general-purpose embedding model with strong performance
  on semantic similarity tasks relative to its size, making it a reasonable
  default choice without requiring domain-specific fine-tuning for this
  project's scope

Trade-off: Larger embedding models (e.g., all-mpnet-base-v2) typically
produce somewhat higher-quality embeddings at the cost of slower inference
and a larger download. Given the small document corpus and the project's
infrastructure constraints, the speed/size benefit of MiniLM was judged to
outweigh the modest quality difference for this use case.

## 4. Vector Database

FAISS was selected over ChromaDB, Pinecone, and Weaviate. Full comparison
and reasoning is documented separately in
Project documents/Tracker/Vector_DB_Comparison.md. Summary: FAISS requires
no separate infrastructure, has no cost, and is sufficient for this
project's data scale (well under 1,000 vectors currently, with headroom to
roughly 1 million before its performance characteristics would become a
limiting factor).

## 5. Retrieval Pipeline

Implemented in backend/app/rag/retriever.py:

1. Load the persisted FAISS index from disk
2. Embed the incoming query using the same MiniLM model used at ingestion
   time (consistency between query and document embeddings is required for
   meaningful similarity comparison)
3. Run similarity_search (for the LLM-answering path) or
   similarity_search_with_score (for the /retrieve diagnostic endpoint)
   against the index
4. Return the top-k (default 4) chunks, each annotated with source
   filename and, where requested, a raw L2 distance score

Note on similarity scores: FAISS's similarity_search_with_score
returns an L2 distance, not a normalized 0-1 similarity percentage — lower
values indicate closer matches. This is reported as-is via the /retrieve
endpoint rather than converted to a potentially misleading "similarity
percentage," to avoid overstating precision the underlying metric doesn't
actually provide.

Reranking: not implemented. See Known Limitations in the README and
Architecture document.

## 6. Agent Orchestration

LangGraph was used to implement the multi-agent pipeline as an explicit
state graph rather than a single large prompt or a simple sequential script,
because:
- Different query types genuinely need different subsets of work (a
  database question doesn't need document retrieval, and vice versa) —
  conditional routing avoids unnecessary LLM calls and unnecessary context
  injection
- Each agent has a single, narrow responsibility (planning, retrieving,
  querying, reasoning, evaluating), which made the system easier to debug
  incrementally during development — each agent could be tested in
  isolation before being wired into the full graph (this incremental
  approach is reflected in the project's build order: Planner and Retriever
  were built and tested standalone before being connected via
  graph.py)
- The shared AgentState (a TypedDict) gives every agent a consistent,
  typed contract for what data is available at each point in the pipeline

## 7. LLM Provider and Model Selection

Groq was selected primarily for its free tier and low-latency inference,
suitable for a student project without a production budget. The originally
selected model, llama-3.1-8b-instant, was deprecated by Groq during
development (announced June 17, 2026); the project was migrated to
openai/gpt-oss-20b across all LLM call sites (retriever, planner, graph,
MCP agent, reasoning agent, evaluator agent, OCR structuring). For vision
tasks, Groq's meta-llama/llama-4-scout-17b-16e-instruct multimodal model
was used instead of self-hosting BLIP or LLaVA, since it was already
available through the same provider and avoided the infrastructure cost of
running a separate vision model locally.

## 8. OCR Implementation

EasyOCR was used per the original specification. It performs raw text
extraction only; a separate LLM call (ocr.py, structure_prescription)
then converts that raw text into structured medicine/dosage/frequency
fields, explicitly instructed to extract only what is clearly present in
the OCR output rather than infer missing fields, to avoid fabricating
prescription details that weren't actually legible or present.

## 9. Database Integration Approach

The 4 required database functions
(get_patient_history, get_lab_results, search_patients,
get_payment_summary) were implemented in backend/app/mcp/tools.py using
direct psycopg2 queries through a connection helper
(backend/app/mcp/connector.py). A FastMCP-based server
(backend/app/mcp/server.py) wraps these same functions to satisfy the
required MCP server file structure, but the live agent path
(backend/app/agents/mcp_agent.py) calls the tool functions directly
in-process rather than through MCP's client/server transport layer. This
was a deliberate scope decision to avoid the added complexity of a separate
MCP transport setup within a single-process FastAPI application, while
still meeting the functional requirement of 4 working database query tools
demonstrably operating against real production data.

## 10. Error Handling Philosophy

Throughout the codebase, agents are designed to fail gracefully rather than
crash or fabricate answers when data is missing or a step fails:
- get_patient_history() returns a clear note when demographic data is
  missing rather than raising an error (addressing a real data gap found
  in the provided database — see Requirements document, Section 4)
- The Reasoning Agent is explicitly instructed to state when context
  doesn't answer the question rather than guess
- JSON parsing of LLM outputs (Planner, MCP Agent, Evaluator) includes
  fallback handling for malformed responses rather than letting a parsing
  failure crash the entire request

## 11. Azure Deployment Readiness

The project is structured for Azure deployment and is ready to be presented as
an Azure-compatible solution. The main reasons are:
- The frontend and backend are already separated into independent services,
  which maps directly to Azure Container Apps or Azure App Service
- The application uses environment variables for configuration, which can be
  moved into Azure App Settings or Container App secrets
- The existing Dockerfiles and docker-compose setup provide a clear base for
  Azure container hosting

Azure deployment approach implemented at the design level:
1. Build and push the frontend and backend images to Azure Container Registry
2. Deploy both containers to Azure Container Apps
3. Store the database connection string and API keys in Azure Key Vault
4. Connect the backend to Azure Database for PostgreSQL Flexible Server
5. Enable Azure Monitor and Application Insights for observability

This deployment model preserves the current architecture while adding cloud
scalability, managed secrets, and operational monitoring for a more
production-ready version of the system.
