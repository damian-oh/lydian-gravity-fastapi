# Matches .python-version and requires-python = ">=3.13", and ships uv so the
# image resolves from uv.lock rather than re-resolving at build time.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies in their own layer: rebuilt only when the lockfile changes, not
# on every source edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY app ./app

EXPOSE 8000

# Shell form on purpose, so ${PORT} is expanded at runtime -- the host assigns
# the port and it is not known at build time.
#
# --proxy-headers is not optional. Every throttle (app/core/rate_limit.py, and
# the demo throttle in app/services/demo_service.py) keys on
# request.client.host; without it every visitor is keyed to the proxy's own
# address and each per-client ceiling silently degrades into a global one.
# Trusting every forwarding hop is safe here only because this container's port
# is reachable solely through the platform's proxy, never directly.
CMD uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --proxy-headers \
    --forwarded-allow-ips='*'
