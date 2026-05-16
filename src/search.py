import os
from typing import Callable

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector

load_dotenv()

PROMPT_TEMPLATE = """
CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO"
"""

REQUIRED_ENV = [
    "OPENAI_API_KEY",
    "OPENAI_EMBEDDING_MODEL",
    "OPENAI_LLM_MODEL",
    "DATABASE_URL",
    "PG_VECTOR_COLLECTION_NAME",
]


def _require_env() -> dict:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in the values."
        )
    return {name: os.environ[name] for name in REQUIRED_ENV}


def search_prompt() -> Callable[[str], str]:
    env = _require_env()

    embeddings = OpenAIEmbeddings(model=env["OPENAI_EMBEDDING_MODEL"])

    store = PGVector(
        embeddings=embeddings,
        collection_name=env["PG_VECTOR_COLLECTION_NAME"],
        connection=env["DATABASE_URL"],
        use_jsonb=True,
    )

    llm = ChatOpenAI(model=env["OPENAI_LLM_MODEL"], temperature=0)
    prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)

    def ask(question: str) -> str:
        results = store.similarity_search_with_score(question, k=10)
        contexto = "\n\n---\n\n".join(doc.page_content for doc, _ in results)
        message = prompt.format(contexto=contexto, pergunta=question)
        response = llm.invoke(message)
        return response.content.strip()

    return ask
