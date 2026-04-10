# Vera GCP

Local GCP Compute emulator — 91 resource types (instances, disks, networks, firewalls, load balancers, and more) running on your machine with no GCP account needed.

Check out the [Vera website](https://project-vera.github.io/) for more information.

## Setup

```bash
./install.sh # for Linux and macOS
.\install.ps1 # for Windows
```

This creates a venv, installs dependencies, installs the `gcloud` CLI if missing (macOS/Linux), and generates a `gcpcli` wrapper script in `.venv/bin/`:

- **`gcpcli`** — drop-in for `gcloud compute`, routes all requests to the local emulator with no real GCP credentials required

`install.sh` creates an isolated gcloud config directory at `.venv/vera-gcloud-config/` and a static fake access token file so gcloud never prompts for credentials or account login, regardless of whether you have a real Google Cloud account.

### Prerequisites

- Python 3.13+
- `gcloud` CLI — installed automatically by `install.sh` if missing (macOS via Homebrew, Linux via apt/yum)

## Usage

Start the emulator in one terminal:

```bash
uv run main.py
# GCP Compute Emulator listening on 127.0.0.1:9100
```

Then in another terminal, use `gcpcli` (via `uv run` or with the venv activated):

### gcloud CLI via `uv run gcpcli`

```bash
uv run gcpcli instances list
# Listed 0 items.

uv run gcpcli instances create my-vm \
  --zone=us-central1-a \
  --machine-type=n1-standard-1 \
  --image-family=debian-11 \
  --image-project=debian-cloud
# Created [projects/vera-project/zones/us-central1-a/instances/my-vm].

uv run gcpcli instances describe my-vm --zone=us-central1-a
uv run gcpcli instances stop my-vm --zone=us-central1-a
uv run gcpcli instances delete my-vm --zone=us-central1-a
```

### gcloud CLI with venv activated

```bash
source .venv/bin/activate # for Linux or macOS
. .\.venv\Scripts\Activate.ps1 # for Windows

gcpcli instances list
gcpcli disks list
gcpcli networks list
gcpcli firewall-rules list
gcpcli zones list
gcpcli machine-types list --zones=us-central1-a
```

### Pointing gcloud manually at the emulator

You can also redirect any `gcloud compute` command to the emulator without the wrapper, using `--access-token-file` to bypass credential checks:

```bash
echo "vera-local-token" > /tmp/vera_token.txt

CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE=http://localhost:9100/ \
CLOUDSDK_CORE_PROJECT=vera-project \
gcloud compute instances list --access-token-file=/tmp/vera_token.txt
```

### Google Cloud Compute Python SDK

Install the optional SDK dependency:

```bash
uv sync --extra sdk
# or: uv pip install "google-cloud-compute>=1.0"
```

Then point it at the emulator:

```python
import os
os.environ["CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE"] = "http://localhost:9100/"
os.environ["GOOGLE_OAUTH_ACCESS_TOKEN"] = "vera-local-token"

from google.cloud import compute_v1

client = compute_v1.InstancesClient()
instances = client.list(project="vera-project", zone="us-central1-a")
for instance in instances:
    print(instance.name)
```

## Running Tests

```bash
# Terminal 1 — start the emulator
uv run main.py

# Terminal 2 — run the full gcloud compute test suite
source .venv/bin/activate # for Linux or macOS

bash tests/test.sh
```

`tests/test.sh` covers the full lifecycle of 18 resource types: zones, regions, machine types, networks, subnets, firewall rules, instances (create/stop/start/delete), disks, snapshots, addresses, health checks, backend services, URL maps, target HTTP proxies, forwarding rules, instance templates, and operations.

## Project Structure

```
main.py                        Flask server (port 9100) — GCP Compute REST gateway
install.sh                     Sets up gcpcli wrapper and isolated gcloud config for Linux and macOS
install.ps1                    Sets up gcpcli wrapper and isolated gcloud config for Windows
emulator_core/
├── state.py                   In-memory resource store (GCPState singleton)
├── utils.py                   Shared helpers: operations, pagination, filtering
├── routes.json                Route registry (91 resources, 816 routes)
└── services/                  91 resource backend modules
tests/
├── test.sh                    gcloud compute command test suite (76 commands)
├── cli/gcp_commands.json      Command catalogue with expected outputs
└── tf/                        Terraform example configs (google provider)
```

## Seeded Resources

The emulator pre-populates the following on startup:

| Resource | Name |
|---|---|
| Network | `default` (auto-mode) |
| Zone | `us-central1-a` |
| Region | `us-central1` |
| Machine types | `n1-standard-1/2/4`, `e2-micro/small/medium`, `e2-standard-2/4`, `n2-standard-2/4` |
| Image families | `debian-11/12/10`, `ubuntu-2204-lts/2004-lts`, `centos-7`, `rocky-linux-9` |

## Supported Resources

Vera GCP supports the following GCP Compute resources:

- Addresses (regional and global)
- Autoscalers
- Backend Buckets
- Backend Services (regional and global)
- Disks
- External VPN Gateways
- Firewall Policies
- Firewalls
- Forwarding Rules (regional and global)
- Future Reservations
- Global Network Endpoint Groups
- Global Public Delegated Prefixes
- Health Checks (HTTP, HTTPS, TCP)
- Images and Image Family Views
- Instance Group Manager Resize Requests
- Instance Group Managers
- Instance Groups
- Instance Settings
- Instance Templates
- Instances
- Instant Snapshots
- Interconnect Attachment Groups
- Interconnect Attachments
- Interconnect Groups
- Interconnects
- License Codes
- Licenses
- Machine Images
- Machine Types
- NAT Mappings
- Network Attachments
- Network Edge Security Services
- Network Endpoint Groups
- Network Firewall Policies
- Networks
- Node Groups
- Node Templates
- Node Types
- Organization Security Policies
- Packet Mirrorings
- Projects
- Public Advertised Prefixes
- Public Delegated Prefixes
- Regions
- Reservations
- Resource Policies
- Routers
- Routes
- Security Policies
- Service Attachments
- Snapshots
- SSL Certificates
- SSL Policies
- Subnetworks
- Target gRPC Proxies
- Target HTTP Proxies
- Target HTTPS Proxies
- Target Instances
- Target Pools
- Target SSL Proxies
- Target TCP Proxies
- Target VPN Gateways
- URL Maps
- VPN Gateways
- VPN Tunnels
- Zone Operations
- Zones
