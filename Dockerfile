FROM python:3.12-slim-bookworm

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends antiword \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY config.py .
COPY bot/ ./bot/
COPY scraper/ ./scraper/
COPY scripts/scraper_loop.sh /app/scripts/scraper_loop.sh
RUN chmod +x /app/scripts/scraper_loop.sh

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "bot.main"]
