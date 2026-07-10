import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DATA_ROOT = os.environ.get("DATA_ROOT")
if not DATA_ROOT:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    DATA_ROOT = os.path.join(PROJECT_ROOT, "data")
RAW_DOCS_PATH = os.path.join(DATA_ROOT, "raw_docs")
VECTOR_STORE_PATH = os.path.join(DATA_ROOT, "vector_store")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_documents():
    documents = []
    for filename in os.listdir(RAW_DOCS_PATH):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(RAW_DOCS_PATH, filename)
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            for page in pages:
                page.metadata["source"] = filename
                page.metadata["doc_type"] = "hospital_policy"
            documents.extend(pages)
            print(f"Loaded {filename} ({len(pages)} pages)")
    return documents


def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
    )
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")
    return chunks

def add_to_vector_store(text: str, metadata: dict):
    """Embed and add a single piece of text (e.g. OCR'd prescription) to the
    existing FAISS index, tagged with the given metadata. Creates the index
    if it doesn't exist yet."""
    from langchain_core.documents import Document

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    doc = Document(page_content=text, metadata=metadata)

    if os.path.exists(os.path.join(VECTOR_STORE_PATH, "index.faiss")):
        vector_store = FAISS.load_local(
            VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True
        )
        vector_store.add_documents([doc])
    else:
        vector_store = FAISS.from_documents([doc], embeddings)

    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    vector_store.save_local(VECTOR_STORE_PATH)


def build_vector_store(chunks):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = FAISS.from_documents(chunks, embeddings)
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
    vector_store.save_local(VECTOR_STORE_PATH)
    print(f"Vector store saved to {VECTOR_STORE_PATH}")


def main():
    documents = load_documents()
    if not documents:
        print("No PDF files found in data/raw_docs/. Add files and rerun.")
        return
    chunks = chunk_documents(documents)
    build_vector_store(chunks)


if __name__ == "__main__":
    main()
