# Holds examples

Black-box agents that speak the Holds I/O contract.

| Example | Purpose |
|---|---|
| `deterministic_agent` | Required CI fixture with schema + custom graders |
| `maul_adversity_agent` | Optional Maul proxy lifecycle; task quality stays separate from HTTP recovery |
| `crewai_agent` | CrewAI-shaped external process |
| `langgraph_agent` | LangGraph-shaped external process |
| `openai_compat_agent` | OpenAI-compatible open-model client |

Deterministic CI uses the local stub in `examples_support/openai_stub_client.py`.

Live open-model smoke:

```bash
export HOLDS_LIVE_BASE_URL=http://127.0.0.1:11434/v1
export HOLDS_LIVE_MODEL=llama3.2
uv run pytest -m live
```
