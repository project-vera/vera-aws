#!/usr/bin/env bash
set -e

OS="$(uname -s)"
ENDPOINT="${VERA_ENDPOINT:-http://localhost:5003}"

# --- Check for uv ---
if ! command -v uv >/dev/null 2>&1; then
    echo "==> uv not found, installing..."
    if [ "$OS" = "Darwin" ] || [ "$OS" = "Linux" ]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Ensure uv is in the PATH for the current session
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        echo "!!! uv auto-install only supported on macOS/Linux."
        echo "    See https://astral.sh/uv/install.sh"
        exit 1
    fi
fi

uv sync
source .venv/bin/activate

echo "==> Vera AWS - Installer (endpoint: $ENDPOINT)"

# --- AWS CLI ---
if command -v aws >/dev/null 2>&1; then
    echo "==> AWS CLI found: $(aws --version 2>&1 | head -1)"
else
    echo "==> AWS CLI not found, attempting install..."
    installed=false

    if [ "$OS" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
        brew install awscli && installed=true
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update -qq && sudo apt-get install -y -qq awscli && installed=true
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y aws-cli && installed=true
        fi
    fi

    if [ "$installed" = false ]; then
        echo "!!! Could not auto-install AWS CLI."
        echo "    Install manually: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
fi

# --- Terraform ---
if command -v terraform >/dev/null 2>&1; then
    echo "==> Terraform found: $(terraform version -json 2>/dev/null | head -1)"
else
    echo "==> Terraform not found, attempting install..."
    installed=false

    if [ "$OS" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
        brew install terraform && installed=true
    elif [ "$OS" = "Linux" ]; then
        if command -v apt-get >/dev/null 2>&1; then
            # HashiCorp APT repo
            sudo apt-get update -qq && sudo apt-get install -y -qq gnupg software-properties-common
            curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg 2>/dev/null
            echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list >/dev/null
            sudo apt-get update -qq && sudo apt-get install -y -qq terraform && installed=true
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
            sudo yum install -y terraform && installed=true
        fi
    fi

    if [ "$installed" = false ]; then
        echo "!!! Could not auto-install Terraform (optional, needed for terlocal)."
        echo "    Install manually: https://developer.hashicorp.com/terraform/install"
        echo "    Continuing without Terraform support..."
    fi
fi

# --- AWS credentials ---
mkdir -p ~/.aws
if ! grep -q '\[vera\]' ~/.aws/credentials 2>/dev/null; then
    echo "==> Adding [vera] profile to ~/.aws/credentials"
    printf '\n[vera]\naws_access_key_id = test\naws_secret_access_key = test\nregion = us-east-1\n' >> ~/.aws/credentials
else
    echo "==> AWS [vera] profile already exists"
fi

# --- Wrapper scripts ---
BIN_DIR="$(pwd)/.venv/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/awscli" << EOF
#!/bin/bash
exec aws --endpoint-url="$ENDPOINT" --profile vera "\$@"
EOF
chmod +x "$BIN_DIR/awscli"

cat > "$BIN_DIR/terlocal" << TEOF
#!/bin/bash
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export AWS_DEFAULT_REGION="\${AWS_DEFAULT_REGION:-us-east-1}"

# Generate a provider override that points ec2 at the emulator
OVERRIDE="_vera_override.tf"
if [ ! -f "\$OVERRIDE" ]; then
    cat > "\$OVERRIDE" << 'INNER'
provider "aws" {
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2 = "$ENDPOINT"
  }
}
INNER
fi

terraform "\$@"
TEOF
chmod +x "$BIN_DIR/terlocal"

source .venv/bin/activate
