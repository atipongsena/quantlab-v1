# QuantLab dependency rules

QuantLab keeps domain contracts deterministic and dependency-free so every later
milestone can rely on the same identities, timestamps, and value semantics.

The executable rule is `tests/architecture/test_dependencies.py`:

- `quantlab/domain` may import Python standard library modules.
- `quantlab/domain` may import other modules under `quantlab.domain`.
- `quantlab/domain` must not import application, infrastructure, provider, web,
  UI, FastAPI, Pydantic, SQLAlchemy, LLM, or MCP code.

Later layers depend inward on domain contracts. Domain contracts never call
outward to storage, providers, services, brokers, agents, APIs, dashboards, or
ML frameworks.
