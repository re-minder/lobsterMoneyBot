# syntax=docker/dockerfile:1

# --- Builder: build a Linux-targeted PEX inside Linux ---
FROM python:3.8-slim AS builder
WORKDIR /src

# Install build deps
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel pex

# Copy source
COPY requirements.txt requirements.txt
COPY app app

# Build PEX (Linux CPython 3.8)
RUN mkdir -p /out \
 && pex -D . -r requirements.txt -m app \
      --interpreter-constraint 'CPython==3.8.*' \
      -o /out/bot.pex

# --- Runtime: minimal image with Python 3.8 ---
FROM python:3.8-slim AS runtime
WORKDIR /app

# Copy PEX from builder
COPY --from=builder /out/bot.pex /app/bot.pex

# Create data dir (bind-mount from host recommended)
RUN mkdir -p /app/data

# Default environment (can be overridden)
ENV DATA_DIR=/app/data \
    DB_PATH=/app/data/bot.db

# Run bot
CMD ["python", "/app/bot.pex"]


