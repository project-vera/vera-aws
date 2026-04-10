FROM amazon/dynamodb-local:latest AS dynamodb-local

FROM python:3.13-slim

# Install Java runtime (needed to run DynamoDBLocal.jar)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy DynamoDB Local JAR and native libs from official image
COPY --from=dynamodb-local /home/dynamodblocal/DynamoDBLocal.jar /dynamodblocal/DynamoDBLocal.jar
COPY --from=dynamodb-local /home/dynamodblocal/DynamoDBLocal_lib /dynamodblocal/DynamoDBLocal_lib

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY main.py state_machine.py ./
COPY emulator_core/ emulator_core/

ENV VERA_HOST=0.0.0.0
ENV VERA_PORT=5005
ENV DYNAMODB_LOCAL_URL=http://localhost:8000
# Override default JAR path for Docker (JAR is at /dynamodblocal, not ./dynamodb-local)
ENV DYNAMODB_LOCAL_JAR=/dynamodblocal/DynamoDBLocal.jar
ENV DYNAMODB_LOCAL_LIB=/dynamodblocal/DynamoDBLocal_lib

EXPOSE 5005

CMD ["uv", "run", "python", "main.py"]
