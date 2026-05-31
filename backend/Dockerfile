FROM python:3.13-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-editable

COPY app/ app/
COPY tools/ tools/
COPY config/ config/

FROM python:3.13-slim

WORKDIR /app

# Create an unprivileged runtime user, and remove the base image's system pip:
# the app runs from /app/.venv (see PATH below), so the /usr/local pip is unused
# at runtime and only adds vulnerable surface — e.g. CVE-2026-3219 /
# CVE-2026-6357 in pip < 26.1, which Trivy flags in the image scan.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser \
    && python -m pip uninstall --yes pip

COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8080/tcp
EXPOSE 5514/udp

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
