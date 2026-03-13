from typing import Dict, Any, List, Union, Optional
from werkzeug.datastructures import MultiDict
import html

# ==================== TYPE ALIASES ====================
# These help clarify what types functions return

RequestParams = Union[MultiDict, Dict[str, List[str]]]
"""Request parameters from werkzeug MultiDict or plain dict with list values."""

Filter = Dict[str, Any]  # {"Name": str, "Values": List[str]}
"""A filter object with Name and Values keys."""

TagSpecification = Dict[str, Any]  # {"ResourceType": str, "Tags": List[{"Key": str, "Value": str}]}
"""A tag specification with ResourceType and Tags keys."""

ErrorResponse = Dict[str, Dict[str, str]]  # {"Error": {"Code": str, "Message": str}}
"""An error response dict that Backend returns for validation failures."""

# ==================== REQUEST PARSING UTILITIES ====================

def get_scalar(params: RequestParams, key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Extract a single scalar string value from request parameters.
    
    Args:
        params: Request parameters (MultiDict or dict)
        key: Parameter key to extract
        default: Default value if key not found (default: None)
    
    Returns:
        The string value for the key, or default if not found.
        Always returns a string or None, never a list.
    
    Example:
        instance_id = get_scalar(params, 'InstanceId')  # Returns: "i-1234" or None
        vpc_id = get_scalar(params, 'VpcId', default='')  # Returns: "vpc-xxx" or ""
    """
    if hasattr(params, 'getlist'):
        vals = params.getlist(key)
        return vals[0] if vals else default
    
    val = params.get(key)
    if isinstance(val, list):
        return val[0] if val else default
    return val if val is not None else default

def get_nested_dict(params: RequestParams, prefix: str) -> Dict[str, Any]:
    """
    Collect all dot-notation nested parameters into a dict.
    E.g., for prefix='LaunchTemplateData', collects LaunchTemplateData.InstanceType,
    LaunchTemplateData.ImageId, etc. into {'InstanceType': ..., 'ImageId': ...}.
    """
    result: Dict[str, Any] = {}
    prefix_dot = prefix + "."
    keys = params.keys() if hasattr(params, 'keys') else params.keys()
    for key in keys:
        if key.startswith(prefix_dot):
            sub_key = key[len(prefix_dot):]
            if sub_key:
                val = params.getlist(key) if hasattr(params, 'getlist') else params.get(key)
                if isinstance(val, list):
                    result[sub_key] = val[0] if len(val) == 1 else val
                else:
                    result[sub_key] = val
    return result

def get_indexed_list(params: RequestParams, base: str) -> List[str]:
    """
    Extract a list of indexed parameters (e.g., InstanceId.1, InstanceId.2, ...).
    
    Args:
        params: Request parameters (MultiDict or dict)
        base: Base parameter name (e.g., "InstanceId" for InstanceId.1, InstanceId.2)
    
    Returns:
        List of string values in order. Empty list if no indexed params found.
    
    Example:
        # For params: InstanceId.1=i-111, InstanceId.2=i-222
        ids = get_indexed_list(params, 'InstanceId')  # Returns: ["i-111", "i-222"]
    """
    result: List[str] = []
    index = 1
    while True:
        key = f"{base}.{index}"
        if key in params:
            if hasattr(params, 'getlist'):
                result.append(params.getlist(key)[0])
            elif isinstance(params.get(key), list):
                result.append(params.get(key)[0])
            else:
                result.append(params.get(key))
            index += 1
        else:
            break
    return result

def parse_filters(params: RequestParams, prefix: str = "Filter") -> List[Filter]:
    """
    Parse AWS-style filters from request parameters.
    
    Args:
        params: Request parameters (MultiDict or dict)
        prefix: Filter prefix (default: "Filter")
    
    Returns:
        List of filter dicts, each with "Name" (str) and "Values" (List[str]) keys.
        Empty list if no filters found.
    
    Example:
        # For params: Filter.1.Name=instance-id, Filter.1.Value.1=i-111
        filters = parse_filters(params)
        # Returns: [{"Name": "instance-id", "Values": ["i-111"]}]
    """
    filters: List[Filter] = []
    index = 1
    while True:
        name_key = f"{prefix}.{index}.Name"
        if name_key not in params:
            break
        
        if hasattr(params, 'getlist'):
            name = params.getlist(name_key)[0]
        else:
            name = params.get(name_key)
            if isinstance(name, list):
                name = name[0]
            
        values: List[str] = []
        val_index = 1
        while True:
            val_key = f"{prefix}.{index}.Value.{val_index}"
            if val_key in params:
                if hasattr(params, 'getlist'):
                    val = params.getlist(val_key)[0]
                else:
                    val = params.get(val_key)
                    if isinstance(val, list):
                        val = val[0]
                values.append(val)
                val_index += 1
            else:
                break
                
        filters.append({"Name": name, "Values": values})
        index += 1
    return filters

def parse_tags(params: RequestParams, prefix_base: str = "TagSpecification") -> List[TagSpecification]:
    """
    Parse AWS-style tag specifications from request parameters.
    
    Args:
        params: Request parameters (MultiDict or dict)
        prefix_base: Tag specification prefix (default: "TagSpecification")
    
    Returns:
        List of tag specification dicts, each with:
        - "ResourceType": str (e.g., "instance", "volume")
        - "Tags": List[{"Key": str, "Value": str}]
        Empty list if no tag specifications found.
    
    Example:
        # For params: TagSpecification.1.ResourceType=instance, 
        #             TagSpecification.1.Tag.1.Key=Name, TagSpecification.1.Tag.1.Value=MyInstance
        tag_specs = parse_tags(params)
        # Returns: [{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "MyInstance"}]}]
    """
    tag_specifications: List[TagSpecification] = []
    index = 1
    while True:
        prefix = f"{prefix_base}.{index}"
        
        has_entry = False
        for k in params.keys():
            if k.startswith(prefix):
                has_entry = True
                break
        
        if not has_entry:
            break
            
        resource_type_key = f"{prefix}.ResourceType"
        if hasattr(params, 'getlist'):
             resource_type = params.getlist(resource_type_key)[0] if resource_type_key in params else ""
        else:
             rt = params.get(resource_type_key)
             if isinstance(rt, list):
                 resource_type = rt[0] if rt else ""
             else:
                 resource_type = rt if rt else ""
        
        tags: List[Dict[str, str]] = []
        tag_index = 1
        while True:
            key_key = f"{prefix}.Tag.{tag_index}.Key"
            value_key = f"{prefix}.Tag.{tag_index}.Value"
            
            if key_key in params or value_key in params:
                if hasattr(params, 'getlist'):
                    k = params.getlist(key_key)[0] if key_key in params else ""
                    v = params.getlist(value_key)[0] if value_key in params else ""
                else:
                    k_val = params.get(key_key)
                    v_val = params.get(value_key)
                    k = k_val[0] if isinstance(k_val, list) and k_val else (k_val or "")
                    v = v_val[0] if isinstance(v_val, list) and v_val else (v_val or "")
                    
                if k:
                    tags.append({"Key": k, "Value": v})
                tag_index += 1
            else:
                break
        
        if tags or resource_type:
            tag_specifications.append({"ResourceType": resource_type, "Tags": tags})
        index += 1
    return tag_specifications

def get_int(params: RequestParams, key: str, default: Optional[int] = None) -> Optional[int]:
    """
    Extract an integer value from request parameters.
    
    Args:
        params: Request parameters (MultiDict or dict)
        key: Parameter key to extract
        default: Default value if key not found or not a valid int (default: None)
    
    Returns:
        The integer value for the key, or default if not found/invalid.
    
    Example:
        max_results = get_int(params, 'MaxResults', default=100)  # Returns: 100 or parsed int
    """
    val = get_scalar(params, key)
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def get_bool(params: RequestParams, key: str, default: bool = False) -> bool:
    """
    Extract a boolean value from request parameters.
    
    Args:
        params: Request parameters (MultiDict or dict)
        key: Parameter key to extract
        default: Default value if key not found (default: False)
    
    Returns:
        True if value is "1", "true", "yes", or "on" (case-insensitive).
        False otherwise, or default if key not found.
    
    Example:
        dry_run = get_bool(params, 'DryRun')  # Returns: True or False
    """
    val = get_scalar(params, key)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")

def str2bool(s: Optional[str], default: bool = False) -> bool:
    """
    Convert a string to a boolean value.
    
    Args:
        s: String to convert (can be None)
        default: Default value if s is None (default: False)
    
    Returns:
        True if s is "1", "true", "yes", or "on" (case-insensitive).
        False otherwise, or default if s is None.
    """
    if s is None:
        return default
    return str(s).strip().lower() in ("1", "true", "yes", "on")

def esc(s: Any) -> str:
    """
    Escape a string for safe XML output.
    
    Args:
        s: Value to escape (will be converted to string)
    
    Returns:
        XML-escaped string with &, <, >, " properly escaped.
    """
    return html.escape(str(s), quote=True)

# ==================== ERROR HANDLING UTILITIES ====================

def create_error_response(code: str, message: str) -> ErrorResponse:
    """
    Create a standardized error response dict.
    
    Backend methods should return this instead of raising exceptions
    for expected error conditions (validation failures, resource not found, etc.).
    
    Args:
        code: AWS error code (e.g., "InvalidInstanceId.Malformed", "ResourceNotFound")
        message: Human-readable error message describing what went wrong
    
    Returns:
        ErrorResponse dict: {"Error": {"Code": str, "Message": str}}
        Frontend serializer will convert this to proper XML error format.
    
    Example:
        # In Backend method:
        if not self.valid_instance_id(instance_id):
            return create_error_response(
                "InvalidInstanceId.Malformed",
                f"The instance ID '{instance_id}' is not valid"
            )
    """
    return {
        "Error": {
            "Code": code,
            "Message": message
        }
    }

def is_error_response(data: Any) -> bool:
    """
    Check if a response dict is an error response.
    
    Used by Frontend and Gateway to detect errors from Backend.
    
    Args:
        data: Response from Backend method (any type)
    
    Returns:
        True if data is a dict with "Error" key (i.e., an ErrorResponse).
        False otherwise.
    
    Example:
        result = backend.DescribeInstances(params)
        if is_error_response(result):
            # Handle error - result is ErrorResponse
            return serialize_error_response(result, request_id)
    """
    return isinstance(data, dict) and "Error" in data

def serialize_error_response(error_data: ErrorResponse, request_id: str) -> str:
    """
    Serialize an error response to AWS EC2 XML format.
    
    Used by Frontend ResponseSerializer to convert error dicts to XML.
    
    Args:
        error_data: ErrorResponse dict from Backend {"Error": {"Code": str, "Message": str}}
        request_id: Request ID for the response
    
    Returns:
        XML error response string in AWS EC2 format.
    
    Example:
        # In ResponseSerializer.serialize():
        if is_error_response(data):
            return serialize_error_response(data, request_id)
    """
    error = error_data.get("Error", {})
    code = esc(error.get("Code", "InternalError"))
    message = esc(error.get("Message", "An error occurred"))
    
    return f"""<Response>
    <Errors>
        <Error>
            <Code>{code}</Code>
            <Message>{message}</Message>
        </Error>
    </Errors>
    <RequestId>{esc(request_id)}</RequestId>
</Response>"""


def apply_filters(resources: List[Any], filters: List[Filter]) -> List[Any]:
    """
    Apply AWS-style filters to a list of resource objects or dicts.

    Each filter has "Name" (str) and "Values" (List[str]).
    - AND logic across filters: resource must match ALL filters.
    - OR logic within Values: resource passes if it matches ANY value.

    Filter name conventions:
    - Hyphens → underscores: "vpc-id" → attribute vpc_id
    - Dot notation: "attachment.status" → obj.attachment["status"] or obj.attachment.status
    - tag: prefix: "tag:Name" → checks resource.tags list for matching Key/Value
    - State dicts: for dict-typed attributes containing a "name" key (e.g. instance_state),
      the "name" value is used for comparison.

    Args:
        resources: List of resource objects (dataclasses) or dicts.
        filters: Already-parsed filter list from params.get("Filter.N", []).

    Returns:
        Filtered list — only resources matching ALL filters.

    Example:
        filtered = apply_filters(list(self.resources.values()), params.get("Filter.N", []))
    """
    if not filters:
        return resources

    result = []
    for resource in resources:
        match = True
        for f in filters:
            name = f.get("Name", "")
            values = f.get("Values", [])
            if not values:
                continue

            # --- tag:Key filter ---
            if name.startswith("tag:"):
                tag_key = name[4:]
                if isinstance(resource, dict):
                    tags = resource.get("tags", []) or resource.get("tagSet", []) or []
                else:
                    tags = getattr(resource, "tags", None) or []
                tag_value = None
                for tag in tags:
                    if isinstance(tag, dict) and tag.get("Key") == tag_key:
                        tag_value = tag.get("Value", "")
                        break
                if tag_value is None or tag_value not in values:
                    match = False
                    break
                continue

            # --- regular attribute filter ---
            attr_path = name.replace("-", "_").split(".")
            obj = resource
            for part in attr_path:
                if obj is None:
                    break
                if isinstance(obj, dict):
                    obj = obj.get(part)
                else:
                    obj = getattr(obj, part, None)

            # Convert to string for comparison
            if obj is None:
                val_str = ""
            elif isinstance(obj, bool):
                val_str = str(obj).lower()
            elif isinstance(obj, dict):
                # State dicts like {"code": 16, "name": "running"} → use "name"
                val_str = str(obj.get("name", ""))
            elif isinstance(obj, list):
                # List field: pass if any element matches any value
                list_strs = [str(item) for item in obj]
                if not any(v in list_strs for v in values):
                    match = False
                    break
                continue
            else:
                val_str = str(obj)

            if val_str not in values:
                match = False
                break

        if match:
            result.append(resource)

    return result
