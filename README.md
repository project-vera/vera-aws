# Vera AWS

Local AWS EC2 emulator. 
Version 0.1 : 89 resource types — VPCs, instances, security groups, volumes, and more (complete list at the end) — running on your machine with no AWS account needed.

## Setup

```bash
./install.sh
```

This creates a venv, installs dependencies, sets up dummy AWS credentials (`~/.aws/credentials`), and generates two wrapper scripts in `.bin/`:

- **`awscli`** — drop-in for `aws`, routes requests to the emulator
- **`terlocal`** — drop-in for `terraform`, configures the AWS provider endpoint

### Prerequisites

- Python 3.10+
- AWS CLI and Terraform are installed automatically by `install.sh` if missing (macOS/Linux)

## Usage

Start the emulator on one terminal:

```bash
uv run main.py
# Running at http://localhost:5003
```

### AWS CLI via `uv run awscli`

```bash
uv run awscli ec2 create-vpc --cidr-block 10.0.0.0/16
# {
#     "Vpc": {
#         "VpcId": "vpc-28bc3a23",
#         "CidrBlock": "10.0.0.0/16",
#         "State": "available",
#         ...
#     }
# }
```

### AWS CLI directly via `awscli`

Simply activate the venv and run `awscli`:
```bash
source .venv/bin/activate

awscli ec2 describe-vpcs
awscli ec2 run-instances --image-id ami-12345678 --instance-type t2.micro
awscli ec2 describe-instances
```

### Terraform

Write standard Terraform — no provider overrides needed:

```hcl
provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
```

Then use `uv run terlocal` instead of `terraform`. Or simply activate the venv and directly run `terlocal`:

```bash
source .venv/bin/activate

terlocal init
terlocal apply -auto-approve
terlocal destroy -auto-approve
```

See `tests/tf/` for more examples.

## Running Tests

```bash
# Terminal 1 — start the emulator
uv run main.py

# Terminal 2 — run 260 CLI commands against it
cd tests
uv run eval_emulator.py test.sh --endpoint http://localhost:5003 \
  --checkpoint eval_results.json --start-from 0
uv run analyze_results.py eval_results.json

# Terraform smoke test
cd tests/tf/00-simple-vpc
uv run terlocal init && uv run terlocal apply -auto-approve
```

| Emulator | Passing (260 commands) |
|---|---|
| LocalStack | 122 (47%) |
| **Vera AWS** | **187 (72%)** |

## Project Structure

```
main.py                        Flask server (port 5003)
install.sh                     Sets up awscli/terlocal wrappers
emulator_core/
├── state.py                   In-memory resource store
├── backend.py                 Base backend class
├── gateway/base.py            Action → backend dispatch
└── services/                  89 resource modules
tests/
├── test.sh                    260 CLI commands (awscli wrapper)
├── eval_emulator.py           Evaluator with checkpointing
└── tf/                        Terraform test cases
```

## Supported Resources

Vera AWS supports the following resources (via EC2 API):

- Account Attributes
- AFIs
- AMIs
- Authorization Rules
- AWS Marketplace
- Block Public Access
- Bundle Tasks
- BYOASN
- BYOIP
- Capacity Reservations
- Carrier Gateways
- Certificate Revocation Lists
- Client Connections
- Client VPN Endpoints
- Configuration Files
- Customer Gateways
- Customer Owned IP Addresses
- Declarative Policies (Account Status Report)
- Dedicated Hosts
- DHCP Options
- EC2 Fleet
- EC2 Instance Connect Endpoints
- EC2 Topology
- Elastic Graphics
- Elastic IP Addresses
- Elastic Network Interfaces
- Encryption
- Event Notifications
- Event Windows For Scheduled Events
- Fast Snapshot Restores
- Infrastructure Performance
- Instance Types
- Instances
- Internet Gateways
- IPAMs
- Key Pairs
- Launch Templates
- Link Aggregation Groups
- Local Gateways
- Managed Prefix Lists
- NAT Gateways
- Network Access Analyzer
- Network ACLs
- Nitro TPM
- Placement Groups
- Pools
- Reachability Analyzer
- Regions And Zones
- Reserved Instances
- Resource Discoveries
- Resource IDs
- Route Servers
- Route Tables
- Routes
- Scheduled Instances
- Scopes
- Security Groups
- Serial Console
- Service Links
- Snapshots
- Spot Fleet
- Spot Instances
- Subnets
- Tags
- Target Networks
- Traffic Mirroring
- Transit Gateway Connect
- Transit Gateway Multicast
- Transit Gateway Peering Attachments
- Transit Gateway Policy Tables
- Transit Gateway Route Tables
- Transit Gateways
- Verified Access Endpoints
- Verified Access Groups
- Verified Access Instances
- Verified Access Logs
- Verified Access Trust Providers
- Virtual Private Gateway Routes
- Virtual Private Gateways
- VM Export
- VM Import
- Volumes
- VPC Endpoint Services
- VPC Endpoints
- VPC Flow Logs
- VPC Peering
- VPCs
- VPN Concentrators
- VPN Connections
