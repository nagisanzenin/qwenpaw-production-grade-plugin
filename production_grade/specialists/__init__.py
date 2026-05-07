"""ACP specialist runners.

Each role (product-manager, software-engineer, etc.) ships as a stdio ACP
server that runs in its own subprocess when QwenPaw calls
``delegate_external_agent(runner="pgs-<role>-<copy>")``. The subprocess
loads the role's SKILL.md + 8 shared protocols as its system prompt — so
each specialist gets a fresh LLM context with only the methodology it
needs, eliminating context drift in long pipelines.

Run a specialist directly for testing::

    python -m production_grade.specialists --role polymath \\
        --plugin-root /Users/.../qwenpaw-production-grade-plugin

The runner expects:
- ``OPENAI_API_KEY`` (or ``DASHSCOPE_API_KEY`` if ``PG_LLM_PROVIDER=dashscope``)
- ``PG_LLM_MODEL`` (defaults: gpt-4o-mini for OpenAI, qwen-max-latest for DashScope)
- Optional ``OPENAI_BASE_URL`` for OpenAI-compatible endpoints (Together, etc.)
"""

__all__: list[str] = []
