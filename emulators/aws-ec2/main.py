import os
import sys
import uuid
import html
import importlib
import inspect
import traceback
import logging
from typing import Dict, Any, Tuple
from flask import Flask, request, Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EC2Emulator")

app = Flask(__name__)

# Registry: Action -> (BackendInstance, ParserClass, SerializerClass)
ACTION_REGISTRY: Dict[str, Tuple[Any, Any, Any]] = {}

# Populated by load_resources()
_serialize_error_response = None

def esc(s):
    return html.escape(str(s), quote=True)

def error_xml(code, message, req_id):
    return (
        f"<Response><Errors>"
        f"<Error><Code>{esc(code)}</Code><Message>{esc(message)}</Message></Error>"
        f"</Errors><RequestID>{esc(req_id)}</RequestID></Response>"
    )

def load_resources(code_dir: str):
    """Load all resource modules from the generated code directory and register actions."""
    if not os.path.exists(code_dir):
        logger.error(f"Generated code directory '{code_dir}' not found.")
        return

    abs_path = os.path.abspath(code_dir)
    parent_dir = os.path.dirname(abs_path)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)

    package_name = os.path.basename(abs_path)
    logger.info(f"Loading resources from package: {package_name}")

    try:
        module = importlib.import_module(package_name)
    except Exception as e:
        logger.error(f"Failed to import package {package_name}: {e}")
        traceback.print_exc()
        return

    # Load serialize_error_response from utils
    global _serialize_error_response
    try:
        utils_mod = importlib.import_module(f"{package_name}.utils")
        _serialize_error_response = utils_mod.serialize_error_response
    except Exception as e:
        logger.warning(f"Could not load serialize_error_response from {package_name}.utils: {e}")

    # Populate default regions if empty
    try:
        state_mod = importlib.import_module(f"{package_name}.services.regionandzone")
        RegionAndZone = state_mod.RegionAndZone
        state_mod2 = importlib.import_module(f"{package_name}.state")
        state = state_mod2.EC2State.get()

        if not state.regions_and_zones:
            default_regions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "eu-west-1", "eu-central-1"]
            for region_name in default_regions:
                state.regions_and_zones[region_name] = RegionAndZone(
                    region_name=region_name,
                    region_endpoint=f"ec2.{region_name}.amazonaws.com",
                    opt_in_status="opt-in-not-required"
                )
                if region_name == "us-east-1":
                    for zone_suffix in ["a", "b", "c", "d", "e", "f"]:
                        zone_name = f"{region_name}{zone_suffix}"
                        zone_id = f"use1-az{ord(zone_suffix) - ord('a') + 1}"
                        state.regions_and_zones[zone_name] = RegionAndZone(
                            zone_name=zone_name,
                            zone_id=zone_id,
                            region_name=region_name,
                            zone_state="available",
                            opt_in_status="opt-in-not-required",
                            zone_type="availability-zone",
                            group_name=region_name,
                            network_border_group=region_name
                        )
    except Exception as e:
        logger.error(f"Failed to populate default regions: {e}")

    # Seed common instance types so RunInstances can validate InstanceType
    try:
        it_mod = importlib.import_module(f"{package_name}.services.instancetype")
        InstanceType = it_mod.InstanceType
        state_mod2 = importlib.import_module(f"{package_name}.state")
        state = state_mod2.EC2State.get()

        if not state.instance_types:
            _INSTANCE_TYPES = [
                # General purpose
                "t2.nano","t2.micro","t2.small","t2.medium","t2.large","t2.xlarge","t2.2xlarge",
                "t3.nano","t3.micro","t3.small","t3.medium","t3.large","t3.xlarge","t3.2xlarge",
                "t3a.nano","t3a.micro","t3a.small","t3a.medium","t3a.large","t3a.xlarge","t3a.2xlarge",
                "t4g.nano","t4g.micro","t4g.small","t4g.medium","t4g.large","t4g.xlarge","t4g.2xlarge",
                "m5.large","m5.xlarge","m5.2xlarge","m5.4xlarge","m5.8xlarge","m5.12xlarge","m5.16xlarge","m5.24xlarge","m5.metal",
                "m5a.large","m5a.xlarge","m5a.2xlarge","m5a.4xlarge","m5a.8xlarge","m5a.12xlarge","m5a.16xlarge","m5a.24xlarge",
                "m6i.large","m6i.xlarge","m6i.2xlarge","m6i.4xlarge","m6i.8xlarge","m6i.12xlarge","m6i.16xlarge","m6i.24xlarge","m6i.32xlarge","m6i.metal",
                "m6a.large","m6a.xlarge","m6a.2xlarge","m6a.4xlarge","m6a.8xlarge","m6a.12xlarge","m6a.16xlarge","m6a.24xlarge","m6a.32xlarge","m6a.48xlarge","m6a.metal",
                "m7i.large","m7i.xlarge","m7i.2xlarge","m7i.4xlarge","m7i.8xlarge","m7i.12xlarge","m7i.16xlarge","m7i.24xlarge","m7i.48xlarge","m7i.metal-24xl","m7i.metal-48xl",
                # Compute optimized
                "c5.large","c5.xlarge","c5.2xlarge","c5.4xlarge","c5.9xlarge","c5.12xlarge","c5.18xlarge","c5.24xlarge","c5.metal",
                "c5a.large","c5a.xlarge","c5a.2xlarge","c5a.4xlarge","c5a.8xlarge","c5a.12xlarge","c5a.16xlarge","c5a.24xlarge",
                "c6i.large","c6i.xlarge","c6i.2xlarge","c6i.4xlarge","c6i.8xlarge","c6i.12xlarge","c6i.16xlarge","c6i.24xlarge","c6i.32xlarge","c6i.metal",
                "c7i.large","c7i.xlarge","c7i.2xlarge","c7i.4xlarge","c7i.8xlarge","c7i.12xlarge","c7i.16xlarge","c7i.24xlarge","c7i.48xlarge","c7i.metal-24xl","c7i.metal-48xl",
                # Memory optimized
                "r5.large","r5.xlarge","r5.2xlarge","r5.4xlarge","r5.8xlarge","r5.12xlarge","r5.16xlarge","r5.24xlarge","r5.metal",
                "r6i.large","r6i.xlarge","r6i.2xlarge","r6i.4xlarge","r6i.8xlarge","r6i.12xlarge","r6i.16xlarge","r6i.24xlarge","r6i.32xlarge","r6i.metal",
                "x2idn.16xlarge","x2idn.24xlarge","x2idn.32xlarge","x2idn.metal",
                # Storage optimized
                "i3.large","i3.xlarge","i3.2xlarge","i3.4xlarge","i3.8xlarge","i3.16xlarge","i3.metal",
                "i3en.large","i3en.xlarge","i3en.2xlarge","i3en.3xlarge","i3en.6xlarge","i3en.12xlarge","i3en.24xlarge","i3en.metal",
                # Accelerated (GPU)
                "p2.xlarge","p2.8xlarge","p2.16xlarge",
                "p3.2xlarge","p3.8xlarge","p3.16xlarge",
                "p3dn.24xlarge",
                "p4d.24xlarge",
                "p5.48xlarge",
                "g4dn.xlarge","g4dn.2xlarge","g4dn.4xlarge","g4dn.8xlarge","g4dn.12xlarge","g4dn.16xlarge","g4dn.metal",
                "g5.xlarge","g5.2xlarge","g5.4xlarge","g5.8xlarge","g5.12xlarge","g5.16xlarge","g5.24xlarge","g5.48xlarge",
                "g6.xlarge","g6.2xlarge","g6.4xlarge","g6.8xlarge","g6.12xlarge","g6.16xlarge","g6.24xlarge","g6.48xlarge",
                "inf1.xlarge","inf1.2xlarge","inf1.6xlarge","inf1.24xlarge",
                "inf2.xlarge","inf2.8xlarge","inf2.24xlarge","inf2.48xlarge",
                "trn1.2xlarge","trn1.32xlarge","trn1n.32xlarge",
            ]
            for it_name in _INSTANCE_TYPES:
                state.instance_types[it_name] = InstanceType(instance_type=it_name, current_generation=True)
            logger.info(f"Seeded {len(_INSTANCE_TYPES)} instance types")
    except Exception as e:
        logger.error(f"Failed to seed instance types: {e}")

    # Group exported classes by resource name
    resources = {}
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            if name.endswith("_Backend"):
                res_name = name[:-8].lower()
                resources.setdefault(res_name, {})["backend"] = obj
            elif name.endswith("_RequestParser"):
                res_name = name[:-14].lower()
                resources.setdefault(res_name, {})["parser"] = obj
            elif name.endswith("_ResponseSerializer"):
                res_name = name[:-19].lower()
                resources.setdefault(res_name, {})["serializer"] = obj

    # Register actions
    for res_name, components in resources.items():
        backend_cls = components.get("backend")
        parser_cls = components.get("parser")
        serializer_cls = components.get("serializer")

        if not (backend_cls and parser_cls and serializer_cls):
            logger.warning(f"Skipping {res_name}: missing B:{bool(backend_cls)} P:{bool(parser_cls)} S:{bool(serializer_cls)}")
            continue

        try:
            backend_instance = backend_cls()
        except Exception as e:
            logger.error(f"Failed to instantiate backend for {res_name}: {e}")
            continue

        methods = inspect.getmembers(backend_instance, predicate=inspect.ismethod)
        count = 0
        for method_name, _ in methods:
            if not method_name.startswith("_"):
                ACTION_REGISTRY[method_name] = (backend_instance, parser_cls, serializer_cls)
                count += 1

        logger.info(f"Loaded service: {res_name} ({count} actions)")

    logger.info(f"Total actions registered: {len(ACTION_REGISTRY)}")

@app.route("/", methods=["GET", "POST"])
def handle_request():
    req_id = str(uuid.uuid4())

    action = request.values.get("Action")
    if not action:
        return Response(error_xml("MissingParameter", "The parameter Action is missing", req_id), status=400, mimetype="text/xml")

    handler = ACTION_REGISTRY.get(action)
    if not handler:
        logger.warning(f"Unknown action: {action}")
        return Response(error_xml("InvalidAction", f"The action {action} is not valid for this endpoint", req_id), status=400, mimetype="text/xml")

    backend, parser, serializer = handler

    try:
        params = parser.parse_request(action, request.values)
        logger.info(f"[{action}] Params: {params}")

        method = getattr(backend, action)
        result = method(params)

        # Normalize nextToken: None -> ""
        if isinstance(result, dict) and result.get("nextToken") is None:
            result["nextToken"] = ""

        logger.info(f"[{action}] Result: {result}")

        # Check if backend returned an error response
        if isinstance(result, dict) and "Error" in result:
            if _serialize_error_response is not None:
                xml_error = _serialize_error_response(result, req_id)
            else:
                err = result["Error"]
                xml_error = error_xml(err.get("Code", "InternalError"), err.get("Message", ""), req_id)
            return Response(xml_error, status=400, mimetype="text/xml")

        xml_response = serializer.serialize(action, result, req_id)
        logger.info(f"[{action}] XML: {xml_response}")

        return Response(xml_response, mimetype="text/xml")

    except Exception as e:
        logger.error(f"Error handling {action}: {e}")
        traceback.print_exc()
        msg = str(e)
        code = msg if (" " not in msg and len(msg) < 50) else "InternalFailure"
        return Response(error_xml(code, msg, req_id), status=400, mimetype="text/xml")

if __name__ == "__main__":
    logger.info("Starting EC2 Emulator...")
    load_resources("emulator_core")
    host = os.environ.get("VERA_HOST", "127.0.0.1")
    port = int(os.environ.get("VERA_PORT", "5003"))
    app.run(host=host, port=port, debug=True)
