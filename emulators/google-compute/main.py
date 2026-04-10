#!/usr/bin/env python3
"""
main.py — REST Gateway for GCP Compute Emulator

Routes GCP Compute REST API calls to the emulator_core service backends.
Compatible with the google-cloud-compute Python SDK and gcloud CLI when
pointed at this emulator via CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE.

Usage:
    python main.py
    # or: uv run main.py

Then point your SDK / CLI at http://localhost:9100:
    export CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE=http://localhost:9100/
    gcloud compute instances list --project=my-project
"""

import os
import sys
import re
import json
import uuid
import importlib
import inspect
import traceback
import logging
import argparse
from typing import Dict, Any, Tuple, List, Optional
from flask import Flask, request, Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================================
# Route registry
# ============================================================================
# Each entry: (compiled_regex, param_names, http_method, backend_instance, parser_cls, serializer_cls, method_name)
_ROUTES: List[Tuple] = []

# serialize_gcp_error / get_error_http_code loaded dynamically from emulator_core.utils
_serialize_gcp_error = None
_get_error_http_code = None

# ============================================================================
# In-memory operation cache
# ============================================================================
# Keyed by operation name (e.g. "operation-1234567890").
# Every mutating backend call whose response looks like a GCP Operation is
# stored here automatically.  The operation GET/wait interceptor below serves
# these directly, bypassing the generated ZoneOperation/RegionOperation/
# GlobalOperation backends (which know nothing about cross-backend operations).
_OPERATIONS: Dict[str, Dict] = {}

# Some backend class names use inflected/plural forms that differ from the
# GCP resource type name the parsers actually expect in the request body.
_BACKEND_TO_RESOURCE_TYPE: Dict[str, str] = {
    "Addresse":                    "Address",
    "GlobalAddresse":              "Address",
    "FirewallPolicie":             "FirewallPolicy",
    "NetworkFirewallPolicie":      "FirewallPolicy",
    "RegionNetworkFirewallPolicie":"FirewallPolicy",
    "SecurityPolicie":             "SecurityPolicy",
    "RegionSecurityPolicie":       "SecurityPolicy",
    "SslPolicie":                  "SslPolicy",
    "RegionSslPolicie":            "SslPolicy",
    "ResourcePolicie":             "ResourcePolicy",
    "TargetGrpcProxie":            "TargetGrpcProxy",
    "TargetHttpProxie":            "TargetHttpProxy",
    "TargetHttpsProxie":           "TargetHttpsProxy",
    "RegionTargetHttpProxie":      "TargetHttpProxy",
    "RegionTargetHttpsProxie":     "TargetHttpsProxy",
    "RegionTargetTcpProxie":       "TargetTcpProxy",
    "TargetSslProxie":             "TargetSslProxy",
    "TargetTcpProxie":             "TargetTcpProxy",
    "TargetVpnGateway":            "TargetVpnGateway",
    "GlobalForwardingRule":        "ForwardingRule",
}

# Pre-compiled regexes for operation path interception
_OPS_GET_RE  = re.compile(r"/operations/([^/]+)$")
_OPS_WAIT_RE = re.compile(r"/operations/([^/]+)/wait$")
_OPS_LIST_RE = re.compile(r"/operations$")

# Pre-compiled regexes for machine-types (read-only, no service module)
_MT_LIST_RE = re.compile(r"zones/([^/]+)/machineTypes$")
_MT_GET_RE  = re.compile(r"zones/([^/]+)/machineTypes/([^/]+)$")

# Static machine-type definitions (subset of real GCP types used in tests)
_MACHINE_TYPES: Dict[str, Dict[str, Any]] = {
    "n1-standard-1":  {"id": "3001",   "guestCpus": 1,  "memoryMb": 3840,  "imageSpaceGb": 10, "isSharedCpu": False, "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "1 vCPU, 3.75 GB RAM"},
    "n1-standard-2":  {"id": "3002",   "guestCpus": 2,  "memoryMb": 7680,  "imageSpaceGb": 10, "isSharedCpu": False, "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "2 vCPUs, 7.5 GB RAM"},
    "n1-standard-4":  {"id": "3004",   "guestCpus": 4,  "memoryMb": 15360, "imageSpaceGb": 10, "isSharedCpu": False, "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "4 vCPUs, 15 GB RAM"},
    "e2-micro":       {"id": "334002", "guestCpus": 2,  "memoryMb": 1024,  "imageSpaceGb": 0,  "isSharedCpu": True,  "maximumPersistentDisks": 16,  "maximumPersistentDisksSizeGb": "3072",   "description": "Efficient Instance, 2 vCPU (1/8 shared physical core) and 1 GB RAM"},
    "e2-small":       {"id": "334003", "guestCpus": 2,  "memoryMb": 2048,  "imageSpaceGb": 0,  "isSharedCpu": True,  "maximumPersistentDisks": 16,  "maximumPersistentDisksSizeGb": "3072",   "description": "Efficient Instance, 2 vCPU (1/4 shared physical core) and 2 GB RAM"},
    "e2-medium":      {"id": "334004", "guestCpus": 2,  "memoryMb": 4096,  "imageSpaceGb": 0,  "isSharedCpu": True,  "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "Efficient Instance, 2 vCPU (1/2 shared physical core) and 4 GB RAM"},
    "e2-standard-2":  {"id": "335002", "guestCpus": 2,  "memoryMb": 8192,  "imageSpaceGb": 0,  "isSharedCpu": False, "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "Efficient Instance, 2 vCPUs, 8 GB RAM"},
    "e2-standard-4":  {"id": "335004", "guestCpus": 4,  "memoryMb": 16384, "imageSpaceGb": 0,  "isSharedCpu": False, "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "Efficient Instance, 4 vCPUs, 16 GB RAM"},
    "n2-standard-2":  {"id": "901002", "guestCpus": 2,  "memoryMb": 8192,  "imageSpaceGb": 0,  "isSharedCpu": False, "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "2 vCPUs 8 GB RAM"},
    "n2-standard-4":  {"id": "901004", "guestCpus": 4,  "memoryMb": 16384, "imageSpaceGb": 0,  "isSharedCpu": False, "maximumPersistentDisks": 128, "maximumPersistentDisksSizeGb": "263168", "description": "4 vCPUs 16 GB RAM"},
}


def _make_machine_type_dict(name: str, zone: str, project: str = "vera-project") -> Dict[str, Any]:
    info = _MACHINE_TYPES.get(name, {"id": "0", "guestCpus": 1, "memoryMb": 3840, "description": name})
    return {
        "kind": "compute#machineType",
        "id": info["id"],
        "creationTimestamp": "1969-12-31T16:00:00.000-08:00",
        "name": name,
        "description": info["description"],
        "guestCpus": info["guestCpus"],
        "memoryMb": info["memoryMb"],
        "imageSpaceGb": info["imageSpaceGb"],
        "isSharedCpu": info["isSharedCpu"],
        "maximumPersistentDisks": info["maximumPersistentDisks"],
        "maximumPersistentDisksSizeGb": info["maximumPersistentDisksSizeGb"],
        "zone": zone,
        "selfLink": f"https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/machineTypes/{name}",
    }


# Pre-compiled regex for image family lookups
# gcloud resolves --image-family/--image-project before sending create requests
_IMG_FAMILY_RE = re.compile(r"projects/([^/]+)/global/images/family/([^/]+)$")
_IMG_GET_RE    = re.compile(r"projects/([^/]+)/global/images/([^/?]+)$")

# Static image families (enough to support debian/ubuntu/centos used in tests)
_IMAGE_FAMILIES: Dict[str, Dict[str, Any]] = {
    "debian-cloud/debian-11": {"name": "debian-11-bullseye-v20240110", "family": "debian-11",
                                "description": "Debian GNU/Linux 11 (bullseye)"},
    "debian-cloud/debian-12": {"name": "debian-12-bookworm-v20240110", "family": "debian-12",
                                "description": "Debian GNU/Linux 12 (bookworm)"},
    "debian-cloud/debian-10": {"name": "debian-10-buster-v20240110", "family": "debian-10",
                                "description": "Debian GNU/Linux 10 (buster)"},
    "ubuntu-os-cloud/ubuntu-2204-lts": {"name": "ubuntu-2204-jammy-v20240110", "family": "ubuntu-2204-lts",
                                         "description": "Ubuntu 22.04 LTS"},
    "ubuntu-os-cloud/ubuntu-2004-lts": {"name": "ubuntu-2004-focal-v20240110", "family": "ubuntu-2004-lts",
                                         "description": "Ubuntu 20.04 LTS"},
    "centos-cloud/centos-7": {"name": "centos-7-v20240110", "family": "centos-7",
                               "description": "CentOS 7"},
    "rocky-linux-cloud/rocky-linux-9": {"name": "rocky-linux-9-v20240110", "family": "rocky-linux-9",
                                         "description": "Rocky Linux 9"},
}


def _make_image_dict(img_info: Dict[str, Any], project: str) -> Dict[str, Any]:
    name = img_info["name"]
    return {
        "kind": "compute#image",
        "id": str(abs(hash(name)) % (10**15)),
        "name": name,
        "family": img_info.get("family", ""),
        "description": img_info.get("description", ""),
        "status": "READY",
        "selfLink": f"https://www.googleapis.com/compute/v1/projects/{project}/global/images/{name}",
        "diskSizeGb": "10",
        "sourceType": "RAW",
        "archiveSizeBytes": "0",
        "creationTimestamp": "2024-01-10T00:00:00.000-07:00",
        "labels": {},
    }


def _is_operation(data: Any) -> bool:
    """True if data looks like a GCP Operation resource."""
    return (
        isinstance(data, dict)
        and data.get("kind", "").startswith("compute#operation")
        and "name" in data
    )


def _intercept_operation(path: str, method: str) -> Optional[str]:
    """Return op_name if this is an operation GET or POST-wait request, else None."""
    if method == "GET":
        m = _OPS_GET_RE.search(path)
        if m:
            return m.group(1)
    elif method == "POST":
        m = _OPS_WAIT_RE.search(path)
        if m:
            return m.group(1)
    return None


def _path_template_to_regex(path_template: str) -> Tuple[re.Pattern, List[str]]:
    """Convert 'projects/{project}/zones/{zone}/instances/{instance}' to a compiled regex."""
    param_names = re.findall(r"\{(\w+)\}", path_template)
    pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path_template)
    regex = re.compile(r"(?:^|/)?" + pattern + r"$")
    return regex, param_names


def load_resources(code_dir: str) -> None:
    """Load emulator_core service modules and register REST routes."""
    global _serialize_gcp_error, _get_error_http_code

    abs_path = os.path.abspath(code_dir)
    parent = os.path.dirname(abs_path)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    package_name = os.path.basename(abs_path)
    logger.info(f"Loading GCP resources from package: {package_name}")

    try:
        importlib.import_module(package_name)
    except Exception as e:
        logger.error(f"Failed to import {package_name}: {e}")
        traceback.print_exc()
        return

    try:
        utils_mod = importlib.import_module(f"{package_name}.utils")
        _serialize_gcp_error = utils_mod.serialize_gcp_error
        _get_error_http_code = utils_mod.get_error_http_code
    except Exception as e:
        logger.warning(f"Could not load utils from {package_name}: {e}")

    routes_path = os.path.join(abs_path, "routes.json")
    if not os.path.exists(routes_path):
        logger.error(f"routes.json not found in {abs_path}.")
        return
    with open(routes_path) as f:
        routes_raw = json.load(f)

    try:
        svc_module = importlib.import_module(f"{package_name}.services")
    except Exception as e:
        logger.error(f"Failed to import {package_name}.services: {e}")
        traceback.print_exc()
        return

    def _snake_to_pascal(s: str) -> str:
        """Convert snake_case or mixed-case to PascalCase: 'health_check' → 'HealthCheck'."""
        return "".join(word.capitalize() for word in s.split("_"))

    resource_components: Dict[str, Dict[str, Any]] = {}
    for name, obj in inspect.getmembers(svc_module, inspect.isclass):
        if name.endswith("_Backend"):
            res = name[:-8]
            resource_components.setdefault(res, {})["backend_cls"] = obj
        elif name.endswith("_RequestParser"):
            res = name[:-14]
            res_title = _snake_to_pascal(res)
            resource_components.setdefault(res_title, {})["parser_cls"] = obj
        elif name.endswith("_ResponseSerializer"):
            res = name[:-19]
            res_title = _snake_to_pascal(res)
            resource_components.setdefault(res_title, {})["serializer_cls"] = obj

    backend_instances: Dict[str, Any] = {}
    for res_name, comps in resource_components.items():
        if "backend_cls" not in comps:
            continue
        try:
            backend_instances[res_name] = comps["backend_cls"]()
        except Exception as e:
            logger.error(f"Failed to instantiate {res_name}_Backend: {e}")

    registered = 0
    skipped = 0
    for route in routes_raw:
        res_name = route["resource"]
        method_name = route["method_name"]
        http_method = route["http_method"]
        path = route["path"]

        comps = resource_components.get(res_name, {})
        backend = backend_instances.get(res_name)
        parser_cls = comps.get("parser_cls")
        serializer_cls = comps.get("serializer_cls")

        if not (backend and parser_cls and serializer_cls):
            skipped += 1
            continue

        regex, param_names = _path_template_to_regex(path)
        _ROUTES.append((regex, param_names, http_method.upper(), backend, parser_cls, serializer_cls, method_name))
        registered += 1

    logger.info(f"Registered {registered} routes ({skipped} skipped — missing components)")
    _seed_defaults()


def _seed_defaults() -> None:
    """Pre-populate GCP resources that exist by default in every project."""
    try:
        from emulator_core.state import GCPState
        from emulator_core.services.network import Network
        from emulator_core.services.zone import Zone
        from emulator_core.services.region import Region
    except ImportError:
        return
    state = GCPState.get()
    if "default" not in state.networks:
        state.networks["default"] = Network(
            name="default",
            auto_create_subnetworks=True,
            description="Default network for the project",
        )
        logger.info("Seeded default VPC network")
    _CPU_PLATFORMS_AB = [
        "Ampere Altra",
        "Intel Broadwell",
        "Intel Cascade Lake",
        "Intel Emerald Rapids",
        "AMD Genoa",
        "NVIDIA Grace",
        "Intel Granite Rapids",
        "Intel Haswell",
        "Intel Ice Lake",
        "Intel Ivy Bridge",
        "Google Axion",
        "AMD Milan",
        "AMD Rome",
        "Intel Sandy Bridge",
        "Intel Sapphire Rapids",
        "Intel Skylake",
        "Google Axion",
        "AMD Turin",
    ]
    _CPU_PLATFORMS_F = [
        "Ampere Altra",
        "Intel Broadwell",
        "Intel Cascade Lake",
        "Intel Emerald Rapids",
        "AMD Genoa",
        "Intel Granite Rapids",
        "Intel Haswell",
        "Intel Ice Lake",
        "Intel Ivy Bridge",
        "Google Axion",
        "AMD Milan",
        "AMD Rome",
        "Intel Sandy Bridge",
        "Intel Sapphire Rapids",
        "Intel Skylake",
        "Google Axion",
        "AMD Turin",
    ]
    _CPU_PLATFORMS_C = [
        "Intel Broadwell",
        "Intel Cascade Lake",
        "Intel Emerald Rapids",
        "AMD Genoa",
        "Intel Granite Rapids",
        "Intel Haswell",
        "Intel Ice Lake",
        "Intel Ivy Bridge",
        "Google Axion",
        "AMD Milan",
        "AMD Rome",
        "Intel Sandy Bridge",
        "Intel Sapphire Rapids",
        "Intel Skylake",
        "Google Axion",
        "AMD Turin",
    ]
    if "us-central1-a" not in state.zones:
        state.zones["us-central1-a"] = Zone(
            name="us-central1-a",
            region="us-central1",
            status="UP",
            description="us-central1-a",
            creation_timestamp="1969-12-31T16:00:00.000-08:00",
            id="2000",
            supports_pzs=True,
            available_cpu_platforms=_CPU_PLATFORMS_AB,
        )
        logger.info("Seeded zone us-central1-a")
    if "us-central1-b" not in state.zones:
        state.zones["us-central1-b"] = Zone(
            name="us-central1-b",
            region="us-central1",
            status="UP",
            description="us-central1-b",
            creation_timestamp="1969-12-31T16:00:00.000-08:00",
            id="2001",
            supports_pzs=True,
            available_cpu_platforms=_CPU_PLATFORMS_AB,
        )
        logger.info("Seeded zone us-central1-b")
    if "us-central1-c" not in state.zones:
        state.zones["us-central1-c"] = Zone(
            name="us-central1-c",
            region="us-central1",
            status="UP",
            description="us-central1-c",
            creation_timestamp="1969-12-31T16:00:00.000-08:00",
            id="2002",
            supports_pzs=True,
            available_cpu_platforms=_CPU_PLATFORMS_C,
        )
        logger.info("Seeded zone us-central1-c")
    if "us-central1-f" not in state.zones:
        state.zones["us-central1-f"] = Zone(
            name="us-central1-f",
            region="us-central1",
            status="UP",
            description="us-central1-f",
            creation_timestamp="1969-12-31T16:00:00.000-08:00",
            id="2004",
            supports_pzs=False,
            available_cpu_platforms=_CPU_PLATFORMS_F,
        )
        logger.info("Seeded zone us-central1-f")
    if "us-central1" not in state.regions:
        state.regions["us-central1"] = Region(
            name="us-central1",
            status="UP",
            description="us-central1",
            zones=[
                "https://www.googleapis.com/compute/v1/projects/vera-project/zones/us-central1-a",
                "https://www.googleapis.com/compute/v1/projects/vera-project/zones/us-central1-b",
                "https://www.googleapis.com/compute/v1/projects/vera-project/zones/us-central1-c",
                "https://www.googleapis.com/compute/v1/projects/vera-project/zones/us-central1-f",
            ],
            creation_timestamp="1969-12-31T16:00:00.000-08:00",
            id="1000",
        )
        logger.info("Seeded region us-central1")


def _match_route(path: str, http_method: str) -> Optional[Tuple[Dict[str, str], Any, Any, Any, str]]:
    """Find matching route and extract path params."""
    clean = re.sub(r"^/?(?:compute/[^/]+/)?", "", path.lstrip("/"))

    for regex, param_names, route_method, backend, parser_cls, serializer_cls, method_name in _ROUTES:
        if route_method != http_method.upper():
            continue
        m = regex.search(clean)
        if m:
            path_params = m.groupdict()
            return path_params, backend, parser_cls, serializer_cls, method_name

    return None


# ============================================================================
# Request handler
# ============================================================================

@app.route("/compute/<path:path_rest>", methods=["GET", "POST", "DELETE", "PATCH", "PUT"])
def dispatch_compute(path_rest: str):
    return _dispatch(path_rest)


@app.route("/<path:path_rest>", methods=["GET", "POST", "DELETE", "PATCH", "PUT"])
def dispatch_root(path_rest: str):
    return _dispatch(path_rest)


def _dispatch(path_rest: str) -> Response:
    req_id = str(uuid.uuid4())
    http_method = request.method.upper()

    if http_method == "GET" and _OPS_LIST_RE.search(path_rest):
        items = list(_OPERATIONS.values())
        result = {"kind": "compute#operationList", "id": "0", "items": items}
        logger.info(f"[{http_method}] /{path_rest} → operations list ({len(items)} ops)")
        return Response(json.dumps(result), status=200, mimetype="application/json")

    op_name = _intercept_operation(path_rest, http_method)
    if op_name is not None:
        op = _OPERATIONS.get(op_name)
        if op is None:
            op = {
                "kind": "compute#operation",
                "name": op_name,
                "status": "DONE",
                "progress": 100,
                "operationType": "unknown",
                "id": "0",
            }
        logger.info(f"[{http_method}] /{path_rest} → operation cache hit: {op_name}")
        return Response(json.dumps(op), status=200, mimetype="application/json")

    # Machine-types interceptor (read-only, no service module)
    if http_method == "GET":
        m = _MT_GET_RE.search(path_rest)
        if m:
            zone_name, mt_name = m.group(1), m.group(2)
            project = request.args.get("project", "vera-project")
            logger.info(f"[GET] /{path_rest} → machine-types get: {mt_name} in {zone_name}")
            mt = _make_machine_type_dict(mt_name, zone_name, project)
            return Response(json.dumps(mt), status=200, mimetype="application/json")
        m = _MT_LIST_RE.search(path_rest)
        if m:
            zone_name = m.group(1)
            project = request.args.get("project", "vera-project")
            logger.info(f"[GET] /{path_rest} → machine-types list in {zone_name}")
            items = [_make_machine_type_dict(n, zone_name, project) for n in _MACHINE_TYPES]
            result = {"kind": "compute#machineTypeList", "id": "0", "items": items}
            return Response(json.dumps(result), status=200, mimetype="application/json")

    # Image family/get interceptor — gcloud resolves image-family before sending create
    if http_method == "GET":
        m = _IMG_FAMILY_RE.search(path_rest)
        if m:
            img_project, family = m.group(1), m.group(2)
            key = f"{img_project}/{family}"
            logger.info(f"[GET] /{path_rest} → image family lookup: {key}")
            img_info = _IMAGE_FAMILIES.get(key)
            if img_info:
                return Response(json.dumps(_make_image_dict(img_info, img_project)), status=200, mimetype="application/json")
            # Also try without project prefix (e.g. just family name)
            for k, v in _IMAGE_FAMILIES.items():
                if k.endswith(f"/{family}") or v.get("family") == family:
                    return Response(json.dumps(_make_image_dict(v, img_project)), status=200, mimetype="application/json")
            err = {"error": {"code": 404, "message": f"The resource '{family}' was not found", "status": "NOT_FOUND"}}
            return Response(json.dumps(err), status=404, mimetype="application/json")
        m = _IMG_GET_RE.search(path_rest)
        if m:
            img_project, img_name = m.group(1), m.group(2)
            logger.info(f"[GET] /{path_rest} → image get: {img_name} in {img_project}")
            for img_info in _IMAGE_FAMILIES.values():
                if img_info["name"] == img_name or img_info.get("family") == img_name:
                    return Response(json.dumps(_make_image_dict(img_info, img_project)), status=200, mimetype="application/json")
            err = {"error": {"code": 404, "message": f"The resource '{img_name}' was not found", "status": "NOT_FOUND"}}
            return Response(json.dumps(err), status=404, mimetype="application/json")

    match = _match_route(path_rest, http_method)
    if match is None:
        logger.warning(f"No route: {http_method} /{path_rest}")
        return Response(
            json.dumps({"error": {"code": 404, "message": f"Unknown API path: /{path_rest}", "status": "NOT_FOUND"}}),
            status=404, mimetype="application/json"
        )

    path_params, backend, parser_cls, serializer_cls, method_name = match
    logger.info(f"[{http_method}] /{path_rest} → {type(backend).__name__}.{method_name}  path_params={path_params}")

    try:
        body: Dict[str, Any] = {}
        if request.content_type and "json" in request.content_type and request.data:
            try:
                body = request.get_json(force=True, silent=True) or {}
            except Exception:
                body = {}

        query_params = dict(request.args)

        # Normalize gcloud CLI flat bodies → parser-expected wrapped bodies.
        # gcloud sends {"name": "...", "machineType": "..."} (flat) but the
        # generated parsers expect {"Instance": {...}} / {"Disk": {...}} etc.
        # Heuristic: if the body has no PascalCase top-level key, it's a flat
        # gcloud body that needs wrapping.
        if body and http_method in ("POST", "PUT", "PATCH"):
            has_wrapper = any(k[:1].isupper() for k in body)
            if not has_wrapper:
                _raw_type = type(backend).__name__.replace("_Backend", "")
                resource_type = _BACKEND_TO_RESOURCE_TYPE.get(_raw_type, _raw_type)
                if method_name == "createSnapshot":
                    body = {"Snapshot": body}
                elif method_name == "insert":
                    body = {resource_type: body}

        params = parser_cls.parse_request(method_name, path_params, query_params, body)
        logger.debug(f"  params={params}")

        method = getattr(backend, method_name)
        result = method(params)

        if isinstance(result, dict) and "Error" in result:
            body_str = _serialize_gcp_error(result) if _serialize_gcp_error else json.dumps(result)
            http_code = _get_error_http_code(result) if _get_error_http_code else 400
            return Response(body_str, status=http_code, mimetype="application/json")

        if _is_operation(result):
            _OPERATIONS[result["name"]] = result
            logger.debug(f"  Cached operation: {result['name']}")

        resp_body = serializer_cls.serialize(method_name, result, req_id)
        return Response(resp_body, status=200, mimetype="application/json")

    except Exception as e:
        logger.error(f"Error handling {http_method} /{path_rest}: {e}")
        traceback.print_exc()
        err_body = json.dumps({
            "error": {"code": 500, "message": str(e), "status": "INTERNAL"}
        })
        return Response(err_body, status=500, mimetype="application/json")


# ============================================================================
# Health check
# ============================================================================

@app.route("/", methods=["GET"])
def health():
    return Response(
        json.dumps({"status": "ok", "routes": len(_ROUTES)}),
        status=200, mimetype="application/json"
    )


# ============================================================================
# Entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="GCP Compute Emulator")
    parser.add_argument("--code-dir", default="emulator_core",
                        help="Path to GCP service code directory (default: emulator_core)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    load_resources(args.code_dir)
    logger.info(f"GCP Compute Emulator listening on {args.host}:{args.port}")
    logger.info(f"Set CLOUDSDK_API_ENDPOINT_OVERRIDES_COMPUTE=http://{args.host}:{args.port}/")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
