# Roadmap

---

## ~~Web chat UI~~ ✓ implemented

`webapp/` — FastAPI + SSE + vanilla JS. Launch with `uv run webapp` (`http://127.0.0.1:8080`).

Tool calls appear live in a collapsible `<details>` box while the agent is working and collapse when the reply arrives. Conversation history survives page refresh. Localhost only.

---

## Packaging for non-technical users

Goal: zero-setup install for someone with no Python environment. PyInstaller is not viable — marker-pdf's torch/transformers dependencies don't bundle cleanly.

### Recommended approach: Docker + Compose

User installs Docker Desktop, then runs `docker-compose up`. The Streamlit UI is exposed on `localhost:8501`.

**Volume mounts needed:**
- `~/.seshat/` — config and ChromaDB store (persists between restarts)
- Obsidian vault path — mounted read-only; path set via env var at compose time
- HuggingFace model cache (`~/.cache/huggingface/`) — must be a named volume or models re-download on every restart

**API key:** passed as an env var in `docker-compose.yml`, not baked into the image.

**Image size:** expect 4–6 GB due to marker-pdf pulling in torch, transformers, and surya models.

### Shorter-term alternative: install script

A `curl | sh` script that installs `uv` (a single binary that manages its own Python) and runs `uv sync`. Simpler than Docker, still requires a terminal step. Suitable for researchers who are comfortable with a command line but don't want to manage a Python environment manually.

### Design constraints Docker introduces

- **Vault path** must be configurable at runtime via env var (not hardcoded in `config.toml`) and the UI should handle a missing or unmounted vault gracefully.
- **Model downloads** happen on first container start and must be cached in a persistent named volume.
- **`vault-chat` terminal loop** is replaced by Streamlit's per-request model — each user message triggers one `agentic_turn()` call rather than a blocking loop. This is actually a cleaner fit.
