import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

REQUIRED_ENV = [
    "OPENAI_API_KEY",
    "OPENAI_EMBEDDING_MODEL",
    "DATABASE_URL",
    "PG_VECTOR_COLLECTION_NAME",
    "PDF_PATH",
]


def _require_env() -> dict:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values."
        )
    return {name: os.environ[name] for name in REQUIRED_ENV}


def ingest_pdf() -> None:
    env = _require_env()

    pdf_path = Path(env["PDF_PATH"]).resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found at PDF_PATH={pdf_path}")

    print(f"Loading PDF from {pdf_path} ...")
    documents = PyPDFLoader(str(pdf_path)).load()
    print(f"Loaded {len(documents)} pages.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        add_start_index=False,
    )
    splits = splitter.split_documents(documents)
    print(f"Generated {len(splits)} chunks.")

    for chunk in splits:
        chunk.metadata = {
            "source": chunk.metadata.get("source", str(pdf_path)),
            "page": chunk.metadata.get("page"),
        }

    embeddings = OpenAIEmbeddings(model=env["OPENAI_EMBEDDING_MODEL"])

    store = PGVector(
        embeddings=embeddings,
        collection_name=env["PG_VECTOR_COLLECTION_NAME"],
        connection=env["DATABASE_URL"],
        use_jsonb=True,
    )

    print("Resetting collection to ensure idempotent ingestion ...")
    store.delete_collection()
    store.create_collection()

    print("Indexing chunks into pgvector ...")
    store.add_documents(splits)
    print(f"Done. Stored {len(splits)} chunks in collection "
          f"'{env['PG_VECTOR_COLLECTION_NAME']}'.")


if __name__ == "__main__":
    ingest_pdf()
