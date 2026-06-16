# seshat

arXiv paper digest for a computational biologist. Fetches papers weekly, scores them with an LLM, and writes a ranked Markdown digest. High-scoring papers are indexed into a local knowledge base for conversational retrieval and management.

See [`docs/DESIGN.md`](docs/DESIGN.md) for architecture documentation.

---

## Repository structure

```
├── digest/
│   ├── config.py, errors.py, llm.py   # Shared infrastructure
│   ├── arxiv/                          # arXiv fetching and PDF conversion
│   │   ├── fetch.py
│   │   └── convert.py
│   ├── pipeline/                       # Automated weekly digest
│   │   ├── run.py, score.py, format.py
│   │   └── prompts/prompt_filter_score.md
│   └── kb/                             # Knowledge base management
│       ├── store.py, cli.py
│       └── prompts/paper_summary.md
├── vault_chat/
│   └── chat.py                         # KB agent (vault-chat)
├── docs/
│   ├── DESIGN.md
│   └── CHANGELOG.md
├── run_digest.sh                       # Shell wrapper for launchd
└── pyproject.toml
```

---

## Configuration

All settings live in `~/.seshat/config.toml`. Optional — defaults apply if absent. Environment variables override TOML values.

```toml
[digest]
ollama_model = "gemma4:26b"
output_dir = "~/Documents/papers/digest"
max_results = 10

[rag]
rag_dir = "~/.seshat/rag"

[chat]
provider = "ollama"              # "ollama" | "anthropic"
vault_path = "~/Documents/obsidian"
private_vault_dirs = ["private"] # vault folders accessible to local model only

[auth]
oauth_client_id = ""             # required for kb auth login
```

Env var overrides: `OLLAMA_MODEL`, `ANTHROPIC_MODEL`, `CHAT_PROVIDER`, `VAULT_PATH`.

To customise the agent's behaviour, create `~/.seshat/system_prompt.md`.

---

## Privacy model

Vault notes under `private_vault_dirs` are private — accessible by the local Ollama model only. Papers are always public. When using a cloud provider (Anthropic), queries that match private documents show a warning; private vault files cannot be read.

```
vault/
├── private/    ← local model only
│   └── journal/
└── research/   ← cloud + local
```

---

## Setup

```bash
uv sync
uv pip install -e .
```

Requires [Ollama](https://ollama.com) running locally with the configured model pulled.

---

## Usage

All commands require `uv run` prefix (entry points in `.venv/bin/`). Alternatively, activate the venv once with `source .venv/bin/activate`.

### Weekly digest

```bash
uv run run-digest
```

Fetches ~490 papers from arXiv, scores them, writes a tiered Markdown digest, and automatically indexes papers with score ≥ 9 into the knowledge base.

### Vault chat — KB agent

The primary interface for interacting with the knowledge base. Handles both querying and management through natural language.

```bash
uv run vault-chat                           # uses provider from config
uv run vault-chat ~/path/to/vault           # override vault path
CHAT_PROVIDER=anthropic uv run vault-chat   # use Anthropic for this session
```

The agent has the following tools:

| Tool | What it does |
|---|---|
| `retrieve_papers` | Search indexed papers |
| `search_notes` | Search vault notes |
| `read_file` | Read one vault file in full |
| `add_document` | Add a paper (arXiv URL) or local PDF — see storage modes below |
| `remove_document` | Two-step remove: preview then confirm; optionally delete the local file |
| `list_papers` | List indexed papers |
| `kb_stats` | Paper, note, and chunk counts |
| `index_vault` | Build or rebuild the vault index |
| `refresh_vault` | Incremental vault sync |

Example interactions:

```
You: index my vault
You: add https://arxiv.org/abs/2406.04093, score 9, Track 1
You: add ~/Downloads/paper.pdf as a private document, full text mode
You: what papers do we have on sparse autoencoders?
You: remove the paper about SAE probing
You: what are my notes on transformers?
```

#### Storage modes for `add_document`

When adding a paper or PDF, the agent asks which mode to use if not specified:

| Mode | What happens | Use when |
|---|---|---|
| `summary` (default) | LLM generates a dense ~1000-word summary; 1–2 chunks stored | Most papers — fast and compact |
| `full_text` | PDF downloaded and converted to Markdown; full text chunked | Papers you want to query at paragraph level |

### Knowledge base CLI (`kb`)

For scripted use, batch operations, and initial setup.

```bash
# Vault indexing
uv run kb index-vault
uv run kb index-vault --vault-path ~/path/to/vault --force   # clear and rebuild
uv run kb refresh-vault

# Add a paper by arXiv URL
uv run kb add https://arxiv.org/abs/2406.04093 --score 9 --track "Track 1"
uv run kb add https://arxiv.org/abs/2406.04093 --full-text   # index full PDF text

# Add a local PDF
uv run kb add paper.pdf --visibility private          # private, summary mode
uv run kb add paper.pdf --visibility private --full-text  # private, full text

# Provider for summary generation (defaults to config provider)
uv run kb add https://arxiv.org/abs/2406.04093 --provider anthropic

# Import all previous digest files at once (no LLM call needed)
uv run kb add-digest ~/Documents/papers/digest/
uv run kb add-digest ~/Documents/papers/digest/ --min-score 7

# Inspect
uv run kb list
uv run kb stats

# Remove (shows preview + confirmation; optionally deletes the local file)
uv run kb remove https://arxiv.org/abs/2406.04093
uv run kb remove file:///path/to/paper.pdf --delete-file
```

### Anthropic authentication

**Option 1 — API key:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Option 2 — claude.ai OAuth** (one-time browser flow, persists across sessions):
```bash
uv run kb auth login     # opens browser → saves token to ~/.seshat/auth.json
uv run kb auth status    # check active auth method
```

OAuth requires `oauth_client_id` in `config.toml`. Confirm credentials from [Anthropic's developer docs](https://docs.anthropic.com).

### PDF conversion (standalone)

```bash
uv run convert-pdf --input https://arxiv.org/abs/2301.07041
uv run convert-pdf --input paper.pdf --output-dir ./output
```

---

## Scheduling (macOS launchd)

See [docs/LAUNCHD_SETUP.md](docs/LAUNCHD_SETUP.md). The shell wrapper [run_digest.sh](run_digest.sh) is the launchd target.

---

## Requirements

- [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.com) (for Ollama provider)
- Python ≥ 3.12
