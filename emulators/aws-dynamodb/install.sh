#!/usr/bin/env bash
set -e

OS="$(uname -s)"
ENDPOINT="${VERA_ENDPOINT:-http://localhost:5005}"
DYNAMODB_LOCAL_VERSION="2.5.3"
DYNAMODB_LOCAL_DIR="$(pwd)/dynamodb-local"

echo "==> Vera AWS DynamoDB - Installer (endpoint: $ENDPOINT)"

# --- Check for uv ---
if ! command -v uv >/dev/null 2>&1; then
    echo "==> uv not found, installing..."
    if [ "$OS" = "Darwin" ] || [ "$OS" = "Linux" ]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        echo "!!! uv auto-install only supported on macOS/Linux."
        exit 1
    fi
fi

uv sync
source .venv/bin/activate

# --- Java ---
if ! command -v java >/dev/null 2>&1; then
    echo "==> Java not found, attempting install..."
    if [ "$OS" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
        brew install openjdk && installed=true
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update -qq && sudo apt-get install -y -qq default-jre-headless
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y java-21-amazon-corretto-headless
        fi
    fi
    if ! command -v java >/dev/null 2>&1; then
        echo "!!! Could not auto-install Java."
        echo "    Install manually: https://adoptium.net/"
        exit 1
    fi
fi
echo "==> Java found: $(java -version 2>&1 | head -1)"

# --- DynamoDB Local JAR ---
JAR="$DYNAMODB_LOCAL_DIR/DynamoDBLocal.jar"
if [ -f "$JAR" ]; then
    echo "==> DynamoDB Local JAR already present"
else
    echo "==> Downloading DynamoDB Local $DYNAMODB_LOCAL_VERSION..."
    mkdir -p "$DYNAMODB_LOCAL_DIR"
    TMP_ZIP="$DYNAMODB_LOCAL_DIR/dynamodb-local.zip"
    curl -fsSL \
        "https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.zip" \
        -o "$TMP_ZIP"
    unzip -q "$TMP_ZIP" -d "$DYNAMODB_LOCAL_DIR"
    rm "$TMP_ZIP"
    echo "==> DynamoDB Local installed at $DYNAMODB_LOCAL_DIR"
fi

# --- AWS credentials ---
mkdir -p ~/.aws
if ! grep -q '\[vera\]' ~/.aws/credentials 2>/dev/null; then
    echo "==> Adding [vera] profile to ~/.aws/credentials"
    printf '\n[vera]\naws_access_key_id = test\naws_secret_access_key = test\nregion = us-east-1\n' >> ~/.aws/credentials
else
    echo "==> AWS [vera] profile already exists"
fi

# --- Wrapper script ---
BIN_DIR="$(pwd)/.venv/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/awscli" << EOF
#!/bin/bash
exec aws --endpoint-url="$ENDPOINT" --profile vera "\$@"
EOF
chmod +x "$BIN_DIR/awscli"

echo ""
echo "==> Done. Start the emulator with:"
echo "    uv run python main.py"
echo ""
echo "    Then use the AWS CLI:"
echo "    uv run awscli dynamodb list-tables"
