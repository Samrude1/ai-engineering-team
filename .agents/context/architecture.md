# Architecture Context

## Stack

| Layer     | Technology                  | Role   |
| --------- | --------------------------- | ------ |
| Orchestrator | CrewAI (Python) | Multi-agent sequential task execution |
| UI Framework | Gradio 5+ | Web interface for interactive prompt engineering and output display |
| LLM Backends | OpenRouter (Anthropic Claude 4.5 / OpenAI GPT-4o) | Agent intelligence for architecture, coding, testing, and docs |
| Packaging & Distribution | UV / Hatchling | Fast Python package management and builds |

## System Boundaries

- `app.py` — Web interface, rate limiting, session management, and streaming log bridge.
- `src/engineering_team/crew.py` — Multi-agent definition, model assignment, and sequential Crew setup.
- `src/engineering_team/config/` — YAML configurations for agent roles, goals, backstories, and task descriptions.
- `src/engineering_team/utils.py` — File sanitization (SuperSanitizer), session artifact management, ZIP packaging.
- `output/` — Ephemeral session workspace directories (automatically pruned after 1 hour).

## Storage Model

- **Local Session Directory (`output/<uuid>/`)**: Stores generated code (`<module_name>.py`, `app.py`, `test_<module_name>.py`, `README.md`, `<module_name>_design.md`).
- **ZIP Archives (`output/ai_engineered_*.zip`)**: Bundled project downloads generated on demand for users.

## Auth and Access Model

- Optional HTTP Basic Auth on `app.py` via `GRADIO_AUTH_USER` and `GRADIO_AUTH_PASSWORD`.
- In-memory sliding window rate limiter (15 requests/hour per client IP) to protect LLM inference quotas.
- Ephemeral session isolation via random UUID directories (`output/<uuid>`).

## Invariants

1. Agents must always have `allow_code_execution=False` to prevent host execution of generated code.
2. User-provided module and class names must be sanitized against path traversal before filesystem operations.
3. User requirement prompts must be bounded within `<user_requirements>` tags.
4. Output directory sessions older than 1 hour are automatically deleted to prevent disk leaks.

