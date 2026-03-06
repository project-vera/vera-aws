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

EXPOSE 9100

CMD ["uv", "run", "python", "main.py", "--host", "0.0.0.0", "--port", "9100"]
