FROM ghcr.io/astral-sh/uv:0.9.17 AS uv

FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /usr/local/bin/uv
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY apps/api/README.md ./README.md
COPY apps/api/src ./src
COPY apps/api/migrations ./migrations
RUN uv sync --locked --no-dev

RUN useradd --create-home --uid 10001 competehub \
    && chown -R competehub:competehub /app

USER competehub

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--worker-class", "gthread", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "competehub_api.app:create_app()"]
