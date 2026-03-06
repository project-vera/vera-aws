FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY main.py ./
COPY emulator_core/ emulator_core/

# Bind to all interfaces inside the container
ENV VERA_HOST=0.0.0.0
ENV VERA_PORT=5003

EXPOSE 5003

CMD ["uv", "run", "python", "main.py"]
