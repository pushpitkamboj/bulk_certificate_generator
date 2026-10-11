FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    CERTGEN_HOST=0.0.0.0 \
    CERTGEN_PORT=8000

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "bulk_certificate_generator.main:app", "--host", "0.0.0.0", "--port", "8000"]
