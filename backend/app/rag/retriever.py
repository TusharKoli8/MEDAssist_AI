import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

DATA_ROOT = os.environ.get("DATA_ROOT")
if not DATA_ROOT:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
VECTOR_STORE_PATH = os.path.join(DATA_ROOT, "vector_store")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

PROMPT_TEMPLATE = """You are a hospital knowledge assistant.
Answer the question using ONLY the context below.
If the context does not contain the answer, say you don't have enough information.
Always mention which source document the answer came from.

Context:
{context}

Question:
{question}

Answer:"""


def load_vector_store():
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = FAISS.load_local(
        VECTOR_STORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    return vector_store


def retrieve_context(vector_store, query, top_k=4):
    results = vector_store.similarity_search(query, k=top_k)
    context_parts = []
    for doc in results:
        source = doc.metadata.get("source", "unknown")
        context_parts.append(f"[Source: {source}]\n{doc.page_content}")
    return "\n\n".join(context_parts), results

def retrieve_with_scores(vector_store, query, top_k=4):
    results = vector_store.similarity_search_with_score(query, k=top_k)
    chunks = []
    for doc, score in results:
        chunks.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "page": doc.metadata.get("page", None),
            "similarity_score": float(score),
        })
    return chunks


def answer_question(query):
    vector_store = load_vector_store()
    context, sources = retrieve_context(vector_store, query)

    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        temperature=0,
    )

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    chain = prompt | llm

    response = chain.invoke({"context": context, "question": query})
    return response.content, sources


if __name__ == "__main__":
    test_query = "What is the discharge process?"
    answer, sources = answer_question(test_query)
    print("Question:", test_query)
    print("\nAnswer:\n", answer)
    print("\nSources used:")
    for s in sources:
        print(" -", s.metadata.get("source"))
