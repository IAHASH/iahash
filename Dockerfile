FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal build tools for cryptography + curl for healthcheck
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl sqlite3 \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY iahash ./iahash
COPY api ./api
COPY web ./web
COPY db ./db
COPY docs ./docs
COPY start.sh README.md ./

RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
