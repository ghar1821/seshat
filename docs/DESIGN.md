# Design Document

## Purpose

A personal research tool that:

1. Fetches papers from arXiv weekly and scores them with an LLM
2. Writes a tiered Markdown digest (Must-Read / Worth Reading / Skim)
3. Indexes papers and vault notes into a local knowledge base
4. Provides a conversational agent for querying and managing the knowledge base

---

## Repository layout

```
├── digest/                          # Python package
│   ├── config.py                    # Central configuration
│   ├── errors.py                    # Domain exceptions + retry decorator
│   ├── llm.py                       # LLM provider abstraction
│   │
│   ├── arxiv/                       # arXiv paper fetching and PDF conversion
│   │   ├── fetch.py                 # Fetch papers from arXiv API
│   │   └── convert.py               # Download arXiv PDFs + convert to Markdown
│   │
│   ├── pipeline/                    # Automated weekly digest
│   │   ├── run.py                   # Entry point: orchestrates full digest run
│   │   ├── score.py                 # LLM-based paper scoring
│   │   ├── format.py                # Markdown digest renderer
│   │   └── prompts/
│   │       └── prompt_filter_score.md
│   │
│   └── kb/                          # Knowledge base management
│       ├── store.py                 # Vector store operations (LangChain + ChromaDB)
│       ├── cli.py                   # `kb` CLI entry point
│       └── prompts/
│           └── paper_summary.md
│
├── vault_chat/
│   └── chat.py                      # `vault-chat` entry point (KB agent)
│
├── webapp/
│   ├── app.py                       # FastAPI application (routes, SSE stream, session state)
│   ├── index.html                   # Single-page chat UI (inline CSS + vanilla JS)
│   └── run.py                       # `webapp` entry point (uvicorn launcher)
│
├── tests/
│   ├── conftest.py                  # Shared fixtures (embeddings, isolated store)
│   ├── test_config.py
│   ├── test_errors.py
│   ├── test_arxiv_convert.py
│   ├── test_store.py
│   └── test_llm.py                  # integration — requires live services
│
├── docs/
│   ├── DESIGN.md                    # This file
│   └── CHANGELOG.md
├── run_digest.sh                    # Shell wrapper for launchd
└── pyproject.toml
```

### Module responsibilities at a glance

| Module | Concern |
|---|---|
| `digest/arxiv/` | Fetching papers from arXiv API; downloading and converting PDFs |
| `digest/pipeline/` | Weekly automated digest: scoring, formatting, orchestration |
| `digest/kb/` | Knowledge base: vector store operations and the `kb` CLI |
| `vault_chat/chat.py` | Conversational agent: query and manage via natural language |
| `webapp/` | Browser-based chat UI: FastAPI routes, SSE stream, session state, HTML frontend |
| `digest/llm.py` | Shared: LLM provider abstraction (Ollama + Anthropic) |
| `digest/config.py` | Shared: central configuration |
| `digest/errors.py` | Shared: domain exceptions and retry decorator |

---

## Dependencies

| Package | Purpose |
|---|---|
| `langchain-chroma` | LangChain wrapper over ChromaDB vector store |
| `langchain-huggingface` | HuggingFace embeddings via LangChain |
| `langchain-text-splitters` | `RecursiveCharacterTextSplitter` for document chunking |
| `chromadb` | Underlying persistent vector store (SQLite + HNSW) |
| `sentence-transformers` | Local embedding model (`all-MiniLM-L6-v2`) |
| `anthropic` | Anthropic Claude API client |
| `ollama` | Local Ollama LLM client |
| `marker-pdf` | High-quality PDF-to-Markdown conversion for scientific papers |
| `requests` | HTTP client (arXiv API) |
| `fastapi` | Web framework for the browser UI (`webapp/`) |
| `uvicorn` | ASGI server that runs the FastAPI app |

---

## CLI entry points

All require `uv run` prefix unless the venv is activated (`source .venv/bin/activate`).

| Command | Module | Purpose |
|---|---|---|
| `uv run run-digest` | `digest.pipeline.run:main` | Run the weekly digest pipeline |
| `uv run vault-chat` | `vault_chat.chat:main` | Start the KB agent chat session |
| `uv run kb` | `digest.kb.cli:main` | Manage the knowledge base (CLI) |
| `uv run convert-pdf` | `digest.arxiv.convert:main` | Convert a PDF to Markdown (standalone) |
| `uv run webapp` | `webapp.run:main` | Start the web UI at `http://127.0.0.1:8080` |

---

## Runtime file locations

| Path | Contents |
|---|---|
| `~/.seshat/config.toml` | User configuration |
| `~/.seshat/rag/` | ChromaDB persistent store |
| `~/Documents/papers/digest/` | Weekly digest `.md` output files (configurable) |

---

## Configuration — `digest/config.py`

Resolution order (later wins): defaults → `~/.seshat/config.toml` → env vars.

| Field | Default | Env var | Description |
|---|---|---|---|
| `ollama_model` | `gemma4:26b` | `OLLAMA_MODEL` | Ollama model |
| `anthropic_model` | `claude-sonnet-4-6` | `ANTHROPIC_MODEL` | Anthropic model |
| `output_dir` | `~/Documents/papers/digest` | — | Digest output directory |
| `max_results` | `10` | — | Max papers per digest |
| `arxiv_cats` | 6 categories | — | `[(category, limit), ...]` |
| `rag_dir` | `~/.seshat/rag` | — | ChromaDB storage path |
| `embed_model` | `all-MiniLM-L6-v2` | — | Embedding model |
| `chunk_size` | `2048` | — | Characters per chunk |
| `chunk_overlap` | `256` | — | Overlap between chunks |
| `provider` | `ollama` | `CHAT_PROVIDER` | Active LLM provider |
| `vault_path` | `~/vault` | `VAULT_PATH` | Obsidian vault root |
| `private_vault_dirs` | `["private"]` | — | Vault folders treated as private |
| `anthropic_api_key` | `""` | `ANTHROPIC_API_KEY` | Anthropic API key (alternative to env var) |

---

## Knowledge base — `digest/kb/store.py`

Single LangChain + ChromaDB collection (`knowledge_base`).

### Document schema

```
page_content : str   — chunked text (embedded)
metadata:
  date_added  : str  — ISO timestamp
  doc_type    : str  — "paper" | "note"
  visibility  : str  — "public" | "private"
  source      : str  — arXiv/DOI URL for papers; "local" for vault .md notes;
                       file:/// URI for local PDF notes
  title       : str  — display title
  authors     : str  — papers only
  score       : int  — relevance 0–10, papers only
  track       : str  — research track, papers only
  storage_mode: str  — "summary" | "full_text"
  file_path   : str  — vault-relative path for .md notes; absolute path for local PDF notes
  content_hash: str  — SHA-256 for change detection (notes; also local PDF papers in full_text mode)
```

**`doc_type` rules:**
- arXiv URL → always `"paper"`
- Local PDF → user must specify `"paper"` or `"note"` via `--doc-type`
- Vault `.md` files → always `"note"`

**`storage_mode` rules:**
- `"note"` documents are always `full_text`
- `"paper"` documents default to `"summary"` (LLM-generated ~1000-word summary, 1–2 chunks); `--full-text` stores all PDF chunks

### Privacy model

| | Ollama (local) | Anthropic (cloud) |
|---|---|---|
| `"public"` | ✓ | ✓ |
| `"private"` | ✓ | Raises `PrivacyError`; tool loop terminates immediately |

When a cloud provider query matches only private content, or tries to read a file in a private vault directory, `PrivacyError` is raised from the tool implementation. `agentic_turn()` catches it, removes the orphaned assistant message from `messages` to keep conversation history valid, and returns the error string directly to the user — no further LLM calls are made. This is a prompt-injection defence: private notes may contain adversarial content that must never reach a cloud model.

Files under `private_vault_dirs` folders → `"private"`. All papers → `"public"`.

### Key functions

| Function | Description |
|---|---|
| `get_store()` | Process-wide Chroma singleton |
| `add_paper(paper, summary, score, track)` | Add paper; idempotent by source URL |
| `add_papers_batch(entries)` | Batch add from digest; no extra LLM call |
| `add_texts(content, doc_type, visibility, source, ...)` | Low-level chunk and add |
| `search(query, n_results, visibility, doc_type)` | Semantic search with filters |
| `search_with_privacy_check(query, provider, ...)` | Provider-aware; returns `(results, has_private_hits)` |
| `delete_by_metadata(key, value)` | Delete all chunks matching key=value |
| `count()` · `count_unique_documents()` · `list_papers()` | Inspection |
| `update_file_path(source, new_path)` | Update `file_path` (and `source` URI) for all chunks matching a source; no re-embedding |
| `get_visibility(file_path, vault_root)` | Derive visibility from folder path |
| `index_vault_file(file_path, vault_root)` | Chunk and index one vault file |
| `refresh_vault(vault_root)` | Incremental sync (Phase 1: vault `.md` files; Phase 2: local PDF notes); returns `(added, updated, deleted)` |

---

## arXiv module — `digest/arxiv/`

`fetch.py`:
- `fetch_arxiv(cat, max_results)` — batch fetch by category, `@with_retries`
- `fetch_arxiv_paper(arxiv_id)` — single paper by ID; correct `source` from `<primary_category>` tag
- `deduplicate(papers)` — remove duplicate titles

`convert.py`:
- `parse_arxiv_url(url)` — extract arXiv ID from any URL format
- `download_arxiv_pdf(arxiv_id, dest_dir)` — download PDF
- `convert_pdf(pdf_path, output_dir)` — convert PDF to Markdown via `marker-pdf`
- Standalone CLI: `uv run convert-pdf --input <url|path>`

---

## Digest pipeline — `digest/pipeline/`

`run.py` orchestrates:
```
make_provider(cfg.provider, options={"num_ctx": 196608})
  ↓
fetch_arxiv() × 6 categories  →  ~490 paper dicts
deduplicate()                  →  ~400 unique papers
  ↓
filter_and_score(papers, provider, max_results, PROMPT_PATH)
  →  selected: [{index, track, score, slop, vetted, summary, why}]
  ↓
format_digest()  →  ~/Documents/papers/digest/digest-{date}.md
  ↓
add_papers_batch(score >= 9)  →  knowledge base
```

`score.py` — `filter_and_score()` sends all abstracts in one 192k-token prompt, parses JSON response.
`format.py` — `format_digest()` renders tiered Markdown digest.
`prompts/prompt_filter_score.md` — scoring rubric loaded at run time.

---

## LLM providers — `digest/llm.py`

`ChatProvider` protocol — three methods used across the system:

```python
complete(messages, max_tokens, context_length) -> str
# Single-shot completion. context_length sets Ollama num_ctx; ignored by Anthropic.

summarize(title, source, max_tokens) -> str
# Dense paper summary. source: str (abstract) or Path (PDF → base64).

agentic_turn(messages, tools, dispatch_fn, system) -> str
# Full tool-calling loop. Modifies messages in place.
```

`make_provider(spec, model, options)` factory:
- `"anthropic"` → `AnthropicProvider` (checks `ANTHROPIC_API_KEY` env var, then `config.anthropic_api_key`)
- `"ollama"` or model name → `OllamaProvider`

---

## KB agent — `vault_chat/chat.py`

Single `run_session(vault)` loop using `provider.agentic_turn()`. Every tool call is printed to the terminal (`→ tool_name(args)`) so the user sees each step.

System prompt loaded from `~/.seshat/system_prompt.md` if present; otherwise the built-in default is used. The vault path has no effect on the system prompt.

### Tools

| Tool | Concern | Cloud provider behaviour |
|---|---|---|
| `retrieve_papers` | Search indexed papers | Public only; `PrivacyError` if query only matches private content |
| `search_notes` | Search vault notes | Public only; `PrivacyError` if query only matches private content |
| `read_file` | Read one vault file in full (after search identifies it) | `PrivacyError` for files in `private_vault_dirs` |
| `add_document` | Add a paper or PDF; requires `doc_type` for local PDFs; two storage modes (see below) | Any |
| `update_file_path` | Update stored path for a local document without re-embedding | Any |
| `remove_document` | Two-step remove: preview → confirm; optionally delete local file | Any |
| `list_papers` | List indexed papers | Any |
| `kb_stats` | Document and chunk counts | Any |
| `index_vault` | Incremental vault sync (new/changed/deleted files); `force=true` clears vault `.md` index first while preserving PDF notes | Any |

### `add_document` storage modes

The tool exposes two modes; the LLM asks the user which to use if not specified:

| Mode | Flow | Chunks stored | Best for |
|---|---|---|---|
| `summary` (default for papers) | abstract/PDF → LLM generates ~1000-word summary → chunk | 1–2 | Most papers — fast, compact |
| `full_text` | download PDF → marker-pdf → chunk raw Markdown | Many | Papers the user wants to query at paragraph level |

Notes (`doc_type="note"`) are **always** stored as `full_text` regardless of what the caller requests.

For local PDFs, `doc_type` (`"paper"` or `"note"`), `visibility` (`"public"` / `"private"`), and an optional `title` override are also accepted.

### `remove_document` two-step flow

1. Call without `confirmed` — returns preview: title, type, source, chunk count, and whether a local file would be deleted.
2. The LLM presents the preview and asks the user to confirm.
3. Call with `confirmed=true` (and optionally `delete_file=true`) — executes the deletion.

Passing `confirmed=true` on the first call is explicitly prohibited in the tool description.

---

## Web UI — `webapp/`

Browser-based alternative to `vault-chat`. Runs on `http://127.0.0.1:8080` (localhost only).

**Stack:** FastAPI + Server-Sent Events + vanilla JS. No npm, no build step, no external JS dependencies. The entire frontend is `webapp/index.html` — a single file with inline CSS and JS that any developer can read in one sitting.

**Session state:** a single in-memory dict shared across browser tabs. Appropriate for a local single-user tool.

**Request flow:**

```
Browser POST /chat
  → FastAPI spawns a background thread running provider.agentic_turn()
  → thread pushes {type: "tool"} events to a queue as each tool fires
  → async SSE generator drains the queue (50 ms poll) and yields data: lines
  → thread pushes {type: "reply"} event + sentinel when done
Browser reads the stream via fetch() + ReadableStream
  → tool events: appended live to an open <details> box
  → reply event: <details> collapses; reply bubble appears
```

**Why fetch + ReadableStream instead of EventSource:** `EventSource` only supports `GET`; sending the message body requires `POST`.

---

## Error handling — `digest/errors.py`

```
PaperDigestError
├── FetchError          arXiv API failures
├── LLMError            LLM failures
├── RAGError            Vector store failures
├── AuthenticationError Missing credentials
└── PrivacyError        Cloud provider attempted to access private content
                        (caught by agentic_turn() for an immediate hard stop)
```

`@with_retries(max_attempts, backoff, exceptions)` — used in `arxiv/fetch.py` and `pipeline/score.py`.

---

## Data flows

### Weekly digest

```
arXiv → fetch → deduplicate → score → format digest → index score≥9 papers
```

### Vault chat turn

```
User message → provider.agentic_turn() → tool loop → reply
  retrieve_papers / search_notes  → search_with_privacy_check()
  read_file                       → privacy check → filesystem read
  add_document (summary mode)     → fetch metadata → provider.summarize() → add_texts()
  add_document (full_text mode)   → download PDF → convert_pdf() → chunk → add_texts()
  add_document (note, local PDF)  → convert_pdf() in tempdir → chunk → add_texts(); tempdir auto-deleted
  update_file_path                → update file_path + source URI in all matching chunks; no re-embedding
  remove_document (unconfirmed)   → lookup metadata → return preview
  remove_document (confirmed)     → store.delete() → optionally unlink local file
  index_vault                     → optionally clear vault .md chunks (preserving PDF notes) → refresh_vault()
  refresh_vault Phase 1           → compare hashes → index new/changed vault .md, delete removed (skips PDF notes)
  refresh_vault Phase 2           → check local PDF notes: warn if missing, re-index if hash changed
```
