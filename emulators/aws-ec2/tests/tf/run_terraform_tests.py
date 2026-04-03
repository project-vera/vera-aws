#!/usr/bin/env python3
"""
Minimal Terraform test runner for Vera-AWS and LocalStack.

This script iterates over Terraform testcase directories under `tests/tf/<case>/`,
and for each backend runs the full lifecycle:
  terraform init -> terraform apply -> terraform destroy

To keep environments clean and avoid plugin/state accumulation, each testcase is
copied into a temporary directory and executed there (temp dir is deleted after).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[3]  # emulators/aws-ec2/tests/tf -> emulators/aws-ec2 -> emulators -> repo
DEFAULT_TF_ROOT = Path(__file__).resolve().parent


@dataclass
class BackendConfig:
    name: str
    ec2_endpoint: str


BACKENDS: Dict[str, BackendConfig] = {
    "localstack": BackendConfig(name="localstack", ec2_endpoint="http://localhost:4566"),
    "vera-aws": BackendConfig(name="vera-aws", ec2_endpoint="http://localhost:5003"),
}


def run(cmd: List[str], cwd: Path, env: Dict[str, str], timeout_s: int) -> Tuple[int, str, str]:
    # Do not set executable= here: with a argv list, overriding executable to bash
    # makes the first arg ("terraform") be treated as a script path, breaking init/apply.
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _is_terraform_config_file(p: Path) -> bool:
    if not p.is_file():
        return False
    name = p.name
    return name.endswith(".tf") or name.endswith(".tf.json")


def discover_cases(tf_root: Path) -> List[str]:
    """
    Each sub dir under tf_root is treated as one Terraform testcase.
    We include a dir if it contains at least one *.tf / *.tf.json file (any depth).
    """
    cases: List[str] = []
    for child in sorted(tf_root.iterdir()):
        if not child.is_dir():
            continue
        if any(_is_terraform_config_file(p) for p in child.rglob("*")):
            cases.append(child.name)
    return cases


def copy_case_to_temp(case_dir: Path, tmp_dir: Path) -> Path:
    """
    Copy the testcase contents into a temp working directory.
    We intentionally do NOT copy Terraform state / plugins.
    """

    def ignore(src: str, names: List[str]) -> List[str]:
        ignored: List[str] = []
        for n in names:
            if n == ".terraform" or n.startswith(".terraform/"):
                ignored.append(n)
                continue
            if n == ".terraform.lock.hcl":
                ignored.append(n)
                continue
            if n.startswith("terraform.tfstate"):
                ignored.append(n)
                continue
            if n.endswith("_override.tf") or n.endswith("override.tf"):
                ignored.append(n)
                continue
        return ignored

    dest = tmp_dir / case_dir.name
    shutil.copytree(str(case_dir), str(dest), ignore=ignore, dirs_exist_ok=False)
    return dest


def write_backend_override(tmp_case_dir: Path, backend: BackendConfig) -> Path:
    """
    Write a provider override file that:
      - sets dummy credentials
      - skips credential/account validation
      - points EC2 endpoint to the selected backend

    We do NOT set region, because testcase directories already declare it.
    """
    override_path = tmp_case_dir / "_backend_override.tf"
    override_path.write_text(
        "\n".join(
            [
                'provider "aws" {',
                '  access_key                  = "test"',
                '  secret_key                  = "test"',
                "  skip_credentials_validation = true",
                "  skip_metadata_api_check     = true",
                "  skip_requesting_account_id  = true",
                "",
                "  endpoints {",
                f'    ec2 = "{backend.ec2_endpoint}"',
                "  }",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return override_path


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all Terraform testcases against LocalStack and/or Vera-AWS",
    )
    parser.add_argument(
        "--tf-root",
        type=Path,
        default=DEFAULT_TF_ROOT,
        help=f"Path to terraform testcases root (default: {DEFAULT_TF_ROOT})",
    )
    parser.add_argument(
        "--backend",
        choices=["localstack", "vera-aws", "both"],
        default="both",
        help="Which backend(s) to run against",
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Run only the specified testcase directory name under tf-root (can be repeated)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all discovered testcase directories under tf-root",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=600,
        help="Timeout for terraform init/apply/destroy steps (seconds)",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable Terraform TRACE logs (TF_LOG=TRACE) for each step",
    )

    args = parser.parse_args()

    tf_root: Path = args.tf_root
    if not tf_root.exists():
        print(f"Error: tf_root does not exist: {tf_root}", file=sys.stderr)
        sys.exit(1)

    discovered = discover_cases(tf_root)
    if not discovered:
        print(f"No testcase dirs discovered under: {tf_root}", file=sys.stderr)
        sys.exit(1)

    if args.all:
        cases = discovered
    else:
        cases = args.case
        if not cases:
            print("No testcases selected.", file=sys.stderr)
            print(f"Discovered cases under {tf_root}: {', '.join(discovered)}", file=sys.stderr)
            print("Use --all to run all, or --case <name> to run a specific one.", file=sys.stderr)
            sys.exit(2)

    if args.backend == "both":
        backend_list = [BACKENDS["localstack"], BACKENDS["vera-aws"]]
    else:
        backend_list = [BACKENDS[args.backend]]

    runs_dir = tf_root / "runs"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_root = runs_dir / timestamp
    ensure_dir(run_root)

    results: List[Dict[str, object]] = []

    for backend in backend_list:
        for case in cases:
            case_dir = tf_root / case
            if not case_dir.exists():
                print(f"Skipping missing testcase: {case_dir}", file=sys.stderr)
                continue

            print(f"\n==> Running testcase '{case}' on backend '{backend.name}'")

            backend_dir = run_root / backend.name / case
            ensure_dir(backend_dir)

            t0 = time.time()

            with tempfile.TemporaryDirectory(prefix=f"vera-tf-{backend.name}-{case}-") as tmp:
                tmp_dir = Path(tmp)
                tmp_case_dir = copy_case_to_temp(case_dir, tmp_dir)

                # Inject provider endpoint override for this backend.
                write_backend_override(tmp_case_dir, backend)

                # Ensure we don't accidentally reuse cached .terraform from a previous run.
                # (We already copied testcase without .terraform.)
                env = os.environ.copy()
                env["TF_IN_AUTOMATION"] = "1"
                env["TF_INPUT"] = "0"

                step_results: Dict[str, Dict[str, object]] = {}

                def run_step(step: str, cmd: List[str]) -> None:
                    step_log = backend_dir / f"{step}.log"
                    step_env = env.copy()

                    if args.trace:
                        # Terraform will write its logs to TF_LOG_PATH.
                        step_env["TF_LOG"] = "TRACE"
                        step_env["TF_LOG_PATH"] = str(backend_dir / f"terraform_{step}.trace.log")

                    print(f"  -> {step} ...")

                    rc, stdout, stderr = run(cmd, cwd=tmp_case_dir, env=step_env, timeout_s=args.timeout_s)
                    step_log.write_text(
                        "".join(
                            [
                                f"COMMAND: {' '.join(cmd)}\n",
                                f"RETURN_CODE: {rc}\n",
                                "\nSTDOUT:\n",
                                stdout,
                                "\n\nSTDERR:\n",
                                stderr,
                                "\n",
                            ]
                        ),
                        encoding="utf-8",
                    )

                    step_results[step] = {
                        "return_code": rc,
                        "log_file": str(step_log),
                        "stdout_preview": stdout[:500],
                        "stderr_preview": stderr[:500],
                    }

                run_step("init", ["terraform", "init", "-input=false", "-no-color"])
                run_step("apply", ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"])
                run_step("destroy", ["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"])

                apply_ok = int(step_results["apply"]["return_code"]) == 0
                destroy_ok = int(step_results["destroy"]["return_code"]) == 0

            elapsed = time.time() - t0
            passed = apply_ok and destroy_ok

            results.append(
                {
                    "backend": backend.name,
                    "case": case,
                    "passed": passed,
                    "elapsed_s": round(elapsed, 2),
                    "steps": step_results,
                }
            )

            print(f"==> Done: passed={passed} (apply_ok={apply_ok}, destroy_ok={destroy_ok})")

    summary_path = run_root / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    total = len(results)
    passed = sum(1 for r in results if r.get("passed") is True)
    print("\n" + "=" * 80)
    print("Terraform test run summary")
    print("=" * 80)
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()

