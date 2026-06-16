# Changelog

Prototype stage — no deployments. Changes documented for development reference only.

---

## [current] — project rename to seshat

### Renamed
- GitHub repository: `ghar1821/paper_digest` → `ghar1821/seshat`
- Project package name: `paper-digest` → `seshat` in `pyproject.toml`
- Config directory: `~/.paper_digest/` → `~/.seshat/` (config, auth, RAG store)
- launchd agent label: `com.putri.paper-digest` → `com.putri.seshat`
- launchd plist file: `com.putri.paper-digest.plist` → `com.putri.seshat.plist`

### Docs
- `LAUNCHD_SETUP.md` moved from project root to `docs/`
- `docs/RENAME.md` added — step-by-step rename procedure
- `docs/DESIGN.md` and `docs/CHANGELOG.md` added in prior phase, now tracked alongside

### Changed
- `config.toml` `rag_dir` default updated to `~/.seshat/rag`
- Vector DB cleared for fresh population following documented README steps

---

## [previous] — subpackage restructure and full-text mode

### Architecture
- Reorganised flat `digest/` package into three focused subpackages:
  - `digest/arxiv/` — arXiv fetching (`fetch.py`) and PDF conversion (`convert.py`)
  - `digest/pipeline/` — weekly digest automation (`run.py`, `score.py`, `format.py`, `prompts/`)
  - `digest/kb/` — knowledge base management (`store.py`, `cli.py`, `prompts/`)
- `digest/config.py`, `digest/errors.py`, `digest/llm.py` remain at package root as shared infrastructure

### Added
- `kb add --full-text` flag — stores full PDF text chunked via `RecursiveCharacterTextSplitter` instead of LLM-generated summary; uses marker-pdf for conversion
- `add_document` tool in vault-chat — adds papers by arXiv URL or local PDF path; supports both `summary` and `full_text` modes
- `index_vault` tool in vault-chat — triggers vault indexing or forced re-index conversationally
- Local PDF support in `kb add` — `--visibility` flag controls `public`/`private`
- `read_file` tool in vault-chat — reads a specific vault file by path

### Removed
- `download_must_reads()` from `format.py` — dead code; replaced by `add_papers_batch()` in the pipeline
- Stale `download_must_reads` import from `run.py`

### Changed
- `vault-chat` repositioned as a unified KB agent (query + management), not just a chat interface
- Every tool call in vault-chat now prints `→ tool_name(args)` to the terminal for transparency
- `add_paper` tool renamed to `add_document`; accepts local PDFs in addition to arXiv URLs

---

## [previous] — LangChain migration and privacy model

### Architecture
- Replaced direct ChromaDB usage with LangChain (`langchain-chroma`, `langchain-huggingface`, `langchain-text-splitters`)
- Unified two-collection schema (papers + vault_notes) into a single `knowledge_base` collection
- Flat document schema: `date_added`, `doc_type`, `visibility`, `source` + optional fields
- Privacy model: `visibility: "public" | "private"` — cloud providers search public only; warning when private docs match
- Vault privacy by folder (`private/` → private, all else → public)

### Added
- `search_with_privacy_check()` — provider-aware search
- `add_paper` tool in vault-chat — add papers by arXiv URL conversationally
- `list_papers`, `kb_stats`, `refresh_vault` tools in vault-chat
- `remove_document` — two-step (preview then confirm); shows what will be deleted; optionally deletes local file
- `kb remove --delete-file` flag
- `kb add --visibility` flag for local PDFs
- `docs/` folder with `DESIGN.md` and `CHANGELOG.md`

### Changed
- `kb remove` now shows a preview with title/type/source before asking for confirmation
- `kb clear` requires typing `yes` (not just `y`) and explicitly states no files will be deleted
- `search_vault` tool renamed to `search_notes`; `remove_paper` renamed to `remove_document`

---

## [previous] — Knowledge base and provider abstraction

### Architecture
- `digest/llm.py`: `ChatProvider` protocol, `OllamaProvider`, `AnthropicProvider`, `make_provider()`
- `digest/config.py`: central `Config` dataclass; `~/.seshat/config.toml` + env var overrides
- `digest/errors.py`: domain exceptions + `@with_retries` decorator
- All prompts moved to external `.md` files in `prompts/`

### Added
- `kb` CLI: `add`, `add-digest`, `list`, `stats`, `remove`, `clear`, `index-vault`, `refresh-vault`, `auth`
- `kb add-digest` — import papers from digest files without re-running LLM
- `vault-chat` Anthropic provider via `provider.agentic_turn()`
- `fetch_arxiv_paper()` — single-paper fetch; fixes `source` format bug
- Vault auto-refresh on `vault-chat` startup

### Changed
- `filter_and_score()` accepts `ChatProvider` instead of a model name string
- `vault-chat` single session loop replacing separate Ollama/Anthropic loops
- System prompt no longer injects vault file list (forces search-first behaviour)
- `retrieve_papers()` raises `RAGError` instead of silently returning `[]`

---

## [initial] — First working prototype

### Added
- arXiv fetch pipeline: `fetch_arxiv`, `deduplicate`
- LLM scoring: `filter_and_score` (local Ollama)
- Markdown digest formatter: `format_digest`
- PDF converter: `convert_pdf`, `download_arxiv_pdf`, `parse_arxiv_url`
- Digest pipeline entry point: `run.py`
- Local vector database: ChromaDB, two collections (papers + vault_notes)
- Obsidian vault chat: `vault_chat/chat.py` (Ollama, `read_file` tool)
- macOS launchd scheduling: `run_digest.sh`
