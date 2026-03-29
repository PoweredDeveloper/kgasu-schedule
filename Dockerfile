FROM python:3.12-slim-bookworm

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends antiword \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY bot/ ./bot/
COPY scraper/ ./scraper/

ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Moscow

CMD ["python", "-m", "bot.main"]
