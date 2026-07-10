# Vector Database Comparison: FAISS vs ChromaDB vs Pinecone vs Weaviate

## Purpose

This document explains the reasoning behind selecting FAISS for MediAssist AI's retrieval pipeline. It compares the main vector database options considered during development and justifies the final choice based on project scale, simplicity, and deployment constraints.

## Comparison Table

| Criteria | FAISS | ChromaDB | Pinecone | Weaviate |
|---|---|---|---|---|
| Type | Indexing library | Embedded database | Managed cloud service | Open-source or managed database |
| Search capability | Vector similarity search | Vector search with basic metadata filtering | Vector search with metadata filtering | Hybrid search with vector + keyword support |
| Persistence | Manual file-based persistence | Built-in persistence | Fully managed persistence | Built-in persistence |
| Infrastructure needs | None | None | Cloud account and API key | Self-hosted or managed service |
| Cost | Free | Free | Paid | Free self-hosted, paid managed |
| Setup complexity | Low | Low | Low to moderate | Moderate |
| Suitability for this project | Excellent | Good | Good but more expensive | Good but heavier operationally |

## Why FAISS Was Chosen

MediAssist AI uses a relatively small document corpus for its retrieval workflow. The knowledge base consists of a limited number of hospital-related PDFs, so the system does not currently require the advanced capabilities of a larger managed vector database.

FAISS was selected because it offers:
- low setup complexity
- no extra infrastructure requirement
- no recurring cloud cost
- fast local retrieval for the current project scale
- a simple deployment fit for a single backend service

## Trade-offs

FAISS is a strong choice for this capstone, but it has some limitations:
- it does not provide native metadata filtering
- it does not offer built-in hybrid search or reranking
- it is less suitable for very large or production-scale multi-user systems

These limitations are acknowledged and documented in the project evaluation and architecture notes.

## Conclusion

FAISS is the most appropriate option for MediAssist AI at its current stage because it balances simplicity, cost, and performance well. If the project grows to require richer filtering, hybrid search, or production-scale retrieval infrastructure, Weaviate or Pinecone would be stronger long-term alternatives.
