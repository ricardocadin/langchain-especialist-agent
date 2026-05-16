# langchain-especialist-agent

RAG (Retrieval-Augmented Generation) sobre o release de resultados da Nu Holding.
Lê o PDF, gera embeddings com OpenAI, armazena em PostgreSQL + pgvector e
responde perguntas via CLI usando somente o conteúdo do documento.

## Pré-requisitos

- **Docker daemon ativo** — Docker Desktop, Colima, OrbStack, etc.
  - Em macOS com Colima: `colima start` antes de qualquer `docker` / `docker-compose`.
- **Docker Compose** — `docker compose` (plugin) ou `docker-compose` (standalone).
  - Os comandos abaixo usam `docker-compose` (v2 standalone). Se você tem o plugin,
    troque por `docker compose` (sem hífen).
- **Python 3.11, 3.12 ou 3.13** — **NÃO use Python 3.14** (alguns pacotes pinados,
  ex.: `psycopg-binary==3.2.9`, ainda não têm wheel para 3.14).
- **Chave da OpenAI com créditos ativos** — uma chave válida sem saldo retorna
  `429 insufficient_quota` e a ingestão falha. Confira em
  <https://platform.openai.com/account/billing>.

## Setup (executar uma vez)

Todos os comandos devem ser executados **a partir da raiz deste projeto**
(`langchain-especialist-agent/`).

1. **Variáveis de ambiente**

   ```bash
   cp .env.example .env
   # edite .env e preencha OPENAI_API_KEY
   ```

2. **Ambiente virtual e dependências** — force Python 3.13 (ou 3.12/3.11)

   ```bash
   python3.13 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Subir o banco vetorial**

   ```bash
   docker-compose up -d
   ```

   Aguarde alguns segundos. Confira se o bootstrap rodou de verdade:

   ```bash
   docker-compose logs bootstrap_vector_ext   # deve mostrar "CREATE EXTENSION"
   docker exec postgres_agent_search psql -U postgres -d agent_search -c "\dx"
   # deve listar a extensão "vector"
   ```

4. **Ingestão do PDF** (idempotente — re-executar substitui a coleção):

   ```bash
   python src/ingest.py
   ```

   Saída esperada: `Done. Stored 31 chunks in collection 'earnings_release'.`

   **Importante:** rode com cwd = raiz do projeto, pois `PDF_PATH` no `.env`
   é relativo (`./earnings_press_release.pdf`).

## Uso diário

Com a venv ativada e o container já no ar:

```bash
python src/chat.py
```

Para encerrar o chat: digite `sair`, `exit`, `quit` ou pressione `Ctrl+D`.

## Reiniciar tudo do zero

```bash
# Em outra máquina ou após reinício:
colima start                                  # se usar Colima
docker-compose up -d                          # sobe Postgres + pgvector
source venv/bin/activate                      # ativa venv
python src/chat.py                            # dados já persistidos no volume
```

Se o volume do Postgres foi apagado (`docker-compose down -v`), rode `python src/ingest.py` antes do chat.

## Exemplo de sessão

```
Faça sua pergunta (digite 'sair' para encerrar):

PERGUNTA: Qual foi o crescimento do número de clientes na Nu Holding?
RESPOSTA: Foram adicionados aproximadamente 4 milhões de clientes no 1T26,
levando o total global para mais de 135 milhões de clientes até março de 2026.

PERGUNTA: A Nu Holding está comprando a bolsa de Nova York?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

## Configurações relevantes

| Variável | Default | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | _vazio_ | Chave da OpenAI (precisa ter créditos) |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Modelo de embeddings |
| `OPENAI_LLM_MODEL` | `gpt-5-nano` | Modelo de chat |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5433/agent_search` | Conexão Postgres (driver `psycopg` v3) |
| `PG_VECTOR_COLLECTION_NAME` | `earnings_release` | Nome da coleção pgvector |
| `PDF_PATH` | `./earnings_press_release.pdf` | Caminho do PDF (relativo à cwd) |

## Parâmetros do RAG

- Chunking: `chunk_size=1000`, `chunk_overlap=150`
- Retrieval: `similarity_search_with_score`, `k=10`
- Prompt: restritivo — só responde com base no contexto recuperado.

## Troubleshooting

| Sintoma | Causa provável | Correção |
|---|---|---|
| `colima is not running` | Daemon Docker parado no macOS | `colima start` |
| `unknown command: docker compose` | Apenas o standalone instalado | Use `docker-compose` (com hífen) |
| `ERROR: Could not find a version that satisfies the requirement psycopg-binary==3.2.9` | venv criada com Python 3.14 | Recriar com `python3.13 -m venv venv` |
| `openai.RateLimitError: 429 insufficient_quota` | Conta OpenAI sem créditos | Adicionar saldo em platform.openai.com/account/billing |
| `FileNotFoundError: PDF not found at PDF_PATH=...` (caminho errado) | Script rodado de outro diretório | Executar a partir da raiz do projeto (`cd langchain-especialist-agent`) |
| `\dx` não mostra `vector` após `docker-compose up -d` | Bootstrap falhou silenciosamente | `docker-compose logs bootstrap_vector_ext` para diagnosticar; rodar `docker-compose up -d --force-recreate bootstrap_vector_ext` |

## Estrutura

```
.
├── docker-compose.yml          # Postgres 17 + pgvector + bootstrap da extensão
├── requirements.txt            # Dependências Python (pinadas)
├── .env.example                # Template das variáveis
├── earnings_press_release.pdf  # PDF de origem
├── src/
│   ├── ingest.py               # PDF → chunks → embeddings → pgvector
│   ├── search.py               # Retrieval + prompt + LLM (search_prompt → ask)
│   └── chat.py                 # Loop CLI
└── README.md
```
