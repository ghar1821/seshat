# Roadmap

---

## Web chat UI (Streamlit)

Replace the terminal `vault-chat` loop with a Streamlit web app served on `localhost:8501`. The core agentic logic stays unchanged; the UI is a thin wrapper.

### Tool call transparency

Currently `agentic_turn()` prints tool calls directly to the terminal. To support both contexts without duplicating logic, replace the hardwired `print()` with an optional callback:

```python
def agentic_turn(..., on_tool_call=None):
    # called after each tool execution
    if on_tool_call:
        on_tool_call(name, args, result)
    else:
        print(f"→ {name}({args})")
```

- Terminal mode: pass nothing — existing behaviour preserved.
- Streamlit mode: pass a function that writes to `st.status()`, which renders as a collapsible box with a spinner while running and a summary when done.

This is a small change to `digest/llm.py` and a one-liner at each call site in `vault_chat/chat.py`.

### Session state

`agentic_turn()` already takes a `messages` list and mutates it in place. That maps directly onto `st.session_state.messages` — no restructuring needed.

### Rough implementation size

~100 lines for the Streamlit app, ~20 lines of changes to existing files for the callback abstraction.

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
