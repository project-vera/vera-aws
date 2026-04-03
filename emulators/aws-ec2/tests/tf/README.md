# Terraform test cases (Vera AWS EC2)

This directory holds small Terraform configurations used to exercise the **Vera AWS EC2 emulator** and **LocalStack** without touching real AWS.

**What counts as one testcase:** exactly one **direct child directory** of `tests/tf/` (for example `tests/tf/05-vpc-with-subnet/`). The driver does **not** treat deeper paths like `tests/tf/group/a-case/` as separate testcases—only the top-level folders under `tests/tf/` are candidates.

**When that folder is included:** it must contain at least one `*.tf` or `*.tf.json` file **somewhere under that directory** (the file may live in a subfolder, e.g. `modules/foo/main.tf`). The driver searches recursively **inside** each top-level folder only—not across `tests/tf/` as a whole tree of testcases.

---

## Prerequisites

- **Terraform** installed and on your `PATH` (`terraform -version`).
- For **Vera**: from `emulators/aws-ec2/`, run `./install.sh` once so `terlocal` and `awscli` wrappers exist, then start the emulator:
  ```bash
  uv run main.py
  ```
  Default EC2 endpoint: `http://localhost:5003`.
- For **LocalStack**: start your LocalStack instance (default EC2 endpoint: `http://localhost:4566`).

---

## Running tests with the driver script

`run_terraform_tests.py` runs each testcase in a **temporary directory** (so `.terraform/` and state files are not left inside the testcase folders), injects a **provider override** for the chosen backend (see below), then runs:

`terraform init` → `terraform apply -auto-approve` → `terraform destroy -auto-approve`

Per-step logs and `summary.json` are written under `runs/<timestamp>/` (for example `runs/<timestamp>/vera-aws/05-vpc-with-subnet/apply.log` and `runs/<timestamp>/summary.json`). This directory is gitignored.

From the repository root (you must pass **`--all`** or at least one **`--case`**; there is no default single testcase):

```bash
# One testcase against LocalStack
python3 emulators/aws-ec2/tests/tf/run_terraform_tests.py --backend localstack --case 05-vpc-with-subnet

# One testcase against Vera (emulator must be running)
python3 emulators/aws-ec2/tests/tf/run_terraform_tests.py --backend vera-aws --case 06-instance-in-vpc

# All testcases, both backends (start LocalStack and Vera first)
python3 emulators/aws-ec2/tests/tf/run_terraform_tests.py --backend both --all
```

You can pass `--case` more than once to run several directories (for example `--case 05-vpc-with-subnet --case 06-instance-in-vpc`).

If you omit `--backend`, it defaults to **`both`** (each testcase runs against LocalStack, then against Vera-AWS—start both services first).

Optional flags:

- `--trace` — sets `TF_LOG=TRACE` and writes per-step trace logs next to the other logs (see [Terraform debugging](https://developer.hashicorp.com/terraform/internals/debugging)).
- `--timeout-s N` — per-step timeout in seconds (default `600`).
- `--tf-root PATH` — alternate testcase root (defaults to this directory).

---

## Running tests manually (without the script)

### Vera (`terlocal`)

From `emulators/aws-ec2/`, after `./install.sh`, use **`terlocal`** instead of **`terraform`** inside a testcase directory. The `terlocal` wrapper exports dummy `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (and default region) before calling `terraform`. On first run it also creates `_vera_override.tf` in the **current working directory**, which adds a `provider "aws"` block with skip flags and `endpoints { ec2 = ... }` for the Vera endpoint (`VERA_ENDPOINT` at install time, default `http://localhost:5003`).

```bash
cd emulators/aws-ec2/tests/tf/00-simple-vpc
uv run terlocal init
uv run terlocal apply -auto-approve
uv run terlocal destroy -auto-approve
```

Do not commit `_vera_override.tf` (it is listed in `emulators/aws-ec2/.gitignore`).

### LocalStack or custom endpoints

Point the AWS provider at LocalStack by adding your own override file or extra `provider "aws"` settings with `endpoints { ec2 = "http://localhost:4566" }` and dummy credentials / `skip_*` flags as needed.

### Two styles of `provider "aws"` (both supported)

Testcases in this folder are **not** required to look identical. Roughly:

| Style | Example | What’s in `main.tf` |
|--------|---------|---------------------|
| **A — minimal** | `00-simple-vpc` … `04-one-webserver-with-vars` | Usually only `region = "..."` in `provider "aws"`. |
| **B — inline emulator-friendly** | `05-vpc-with-subnet`, `06-instance-in-vpc` | `region` plus dummy `access_key` / `secret_key` and `skip_*` flags (still **no** `endpoints` in `main.tf`). |

**`run_terraform_tests.py` handles both the same way:** it always adds `_backend_override.tf` in the temp copy, which supplies `endpoints { ec2 = ... }` (and repeats dummy creds / `skip_*` where needed). Terraform **merges** all default `provider "aws"` blocks into one configuration, so Style A and B both end up with a working endpoint for LocalStack or Vera. Style B is convenient when using **`terlocal`** by hand (fewer moving parts in a tiny example).

---

## How Terraform “override” files work

Terraform loads configuration from `*.tf` and `*.tf.json` files in a working directory and **merges** them into one configuration. Files whose names end in **`_override.tf`** (or the legacy `override.tf`) are loaded **after** ordinary `.tf` / `.tf.json` files and are intended for **last-minute adjustments** without editing the main modules.

You can use that to **layer local testing settings on top of the same `provider "aws"` block**:

- **Same provider type, merged:** Multiple `provider "aws" { ... }` blocks without an `alias` are **merged** into one configuration. Later files can add or override attributes (for example `endpoints`, `skip_credentials_validation`).
- **Why we use overrides for emulators:** Real AWS would use normal credentials and default endpoints. For Vera or LocalStack we need fake credentials, skip STS/account checks, and an `endpoints { ec2 = ... }` URL. Keeping that in `*_override.tf` (or generated files like `_vera_override.tf` / `_backend_override.tf`) makes it obvious what is **environment-specific** versus what is **shared testcase HCL**.

In this repo:

| Mechanism | When | What it adds |
|-----------|------|----------------|
| `_vera_override.tf` | Created by `terlocal` in the cwd when you run it | EC2 endpoint + `skip_*` flags for Vera (dummy AWS keys come from the wrapper’s environment, not this file) |
| `_backend_override.tf` | Written by `run_terraform_tests.py` into the **temp** copy of a testcase | EC2 endpoint + dummy creds + skip flags for LocalStack or Vera (merged with whatever the testcase already declares) |

Prefer **not** to commit `endpoints { ec2 = ... }` in testcase `main.tf` when it can be supplied by `terlocal` or the driver override; use dummy credentials only (never real AWS keys).

---

## See also

- `emulators/aws-ec2/README.md` — Vera setup, `terlocal`, and CLI usage.
