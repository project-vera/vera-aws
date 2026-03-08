#!/usr/bin/env python3
"""
Parse amis.json (EC2 describe-images style) and run awscli ec2 register-image
for each AMI. Use -o/--output to write commands to a file instead of running.

To get the all the current AMIs, run:
aws ec2 describe-images --output json > amis.json
"""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _quote(s: str) -> str:
    """Quote for safe use in shell (single-arg)."""
    return shlex.quote(s)


def build_register_image_args(ami: Dict[str, Any]) -> List[str]:
    """Build list of CLI args for one AMI (no leading command)."""
    args: List[str] = []

    name = (ami.get("Name") or "").strip()
    if name:
        args.append(f"--name {_quote(name)}")

    desc = (ami.get("Description") or "").strip()
    if desc:
        args.append(f"--description {_quote(desc)}")

    location = (ami.get("ImageLocation") or "").strip()
    if location:
        args.append(f"--image-location {_quote(location)}")

    arch = (ami.get("Architecture") or "").strip()
    if arch:
        args.append(f"--architecture {_quote(arch)}")

    vtype = (ami.get("VirtualizationType") or "").strip()
    if vtype:
        args.append(f"--virtualization-type {_quote(vtype)}")

    root_dev = (ami.get("RootDeviceName") or "").strip()
    if root_dev:
        args.append(f"--root-device-name {_quote(root_dev)}")

    if ami.get("EnaSupport") is True:
        args.append("--ena-support")

    sriov = (ami.get("SriovNetSupport") or "").strip()
    if sriov:
        args.append(f"--sriov-net-support {_quote(sriov)}")

    boot_mode = (ami.get("BootMode") or "").strip()
    if boot_mode:
        args.append(f"--boot-mode {_quote(boot_mode)}")

    imds = (ami.get("ImdsSupport") or "").strip()
    if imds:
        args.append(f"--imds-support {_quote(imds)}")

    return args


def ami_to_register_image_cmd(ami: Dict[str, Any]) -> str:
    """Build full 'awscli ec2 register-image ...' command for one AMI."""
    args = build_register_image_args(ami)
    if not args:
        return ""
    return "awscli ec2 register-image " + " ".join(args)


def load_amis(path: Path) -> List[Dict[str, Any]]:
    """Load Images array from JSON file (top-level key 'Images')."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    images = data.get("Images")
    if not isinstance(images, list):
        raise ValueError(f"Expected top-level 'Images' array in {path}")
    return images


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse amis.json and generate aws ec2 register-image CLI commands."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "amis_100.json",
        help="Path to amis_100.json (default: warmups/amis_100.json)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Write commands to file instead of running awscli",
    )
    parser.add_argument(
        "--num",
        type=int,
        default=None,
        metavar="N",
        help="Number of AMIs to add (default: all)",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        images = load_amis(args.input)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error loading {args.input}: {e}", file=sys.stderr)
        return 1

    if args.num is not None:
        images = images[: args.num]

    lines = []
    for ami in images:
        cmd = ami_to_register_image_cmd(ami)
        if cmd:
            lines.append(cmd)

    if args.output is not None:
        out = "\n".join(lines) + ("\n" if lines else "")
        args.output.write_text(out, encoding="utf-8")
        print(f"Wrote {len(lines)} commands to {args.output}", file=sys.stderr)
        return 0

    failed = 0
    for i, cmd in enumerate(lines):
        print(f"[{i + 1}/{len(lines)}] {cmd}", file=sys.stderr)
        r = subprocess.run(cmd, shell=True)
        if r.returncode != 0:
            failed += 1
    if failed:
        print(f"{failed} command(s) failed", file=sys.stderr)
        return 1
    return 0


def _test() -> None:
    """Minimal self-test using inline AMI-like dict."""
    ami = {
        "Name": "test-ami",
        "Description": "Test description with spaces",
        "ImageLocation": "amazon/test-ami",
        "Architecture": "x86_64",
        "VirtualizationType": "hvm",
        "RootDeviceName": "/dev/sda1",
        "EnaSupport": True,
        "BlockDeviceMappings": [
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "SnapshotId": "snap-abc123",
                    "VolumeSize": 8,
                    "VolumeType": "gp2",
                    "DeleteOnTermination": True,
                },
            },
        ],
    }
    cmd = ami_to_register_image_cmd(ami)
    assert "awscli ec2 register-image" in cmd
    assert "--name" in cmd and "test-ami" in cmd
    assert "--description" in cmd
    assert "--image-location" in cmd
    assert "--architecture x86_64" in cmd
    assert "--virtualization-type hvm" in cmd
    assert "--ena-support" in cmd
    assert "--block-device-mappings" not in cmd  # ignored for now
    ami2 = {"Name": "ephemeral-ami"}
    cmd2 = ami_to_register_image_cmd(ami2)
    assert "awscli ec2 register-image" in cmd2 and "ephemeral-ami" in cmd2
    print("_test passed", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        _test()
        sys.exit(0)
    sys.exit(main())
