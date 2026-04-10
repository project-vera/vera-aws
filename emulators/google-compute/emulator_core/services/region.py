from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field
import uuid
import random
import json as _json
import re

from ..utils import (
    create_gcp_error, is_error_response,
    make_operation, parse_labels, get_body_param,
)
from ..state import GCPState

@dataclass
class Region:
    quotas: List[Any] = field(default_factory=list)
    deprecated: Dict[str, Any] = field(default_factory=dict)
    creation_timestamp: str = ""
    description: str = ""
    quota_status_warning: Dict[str, Any] = field(default_factory=dict)
    name: str = ""
    zones: List[Any] = field(default_factory=list)
    supports_pzs: bool = False
    status: str = ""
    id: str = ""


    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        d["quotas"] = self.quotas
        if self.deprecated:
            d["deprecated"] = self.deprecated
        if self.creation_timestamp is not None and self.creation_timestamp != "":
            d["creationTimestamp"] = self.creation_timestamp
        if self.description is not None and self.description != "":
            d["description"] = self.description
        d["quotaStatusWarning"] = self.quota_status_warning
        if self.name is not None and self.name != "":
            d["name"] = self.name
        d["zones"] = self.zones
        d["supportsPzs"] = self.supports_pzs
        if self.status is not None and self.status != "":
            d["status"] = self.status
        if self.id is not None and self.id != "":
            d["id"] = self.id
        d["kind"] = "compute#region"
        d["selfLink"] = f"https://www.googleapis.com/compute/v1/projects/vera-project/regions/{self.name}"
        return d

class Region_Backend:
    def __init__(self):
        self.state = GCPState.get()
        self.resources = self.state.regions  # alias to shared store

    def _generate_id(self) -> str:
        return str(random.randint(10**17, 10**18 - 1))

    def _generate_name(self, prefix: str = "region") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:8]}"

    def get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns the specified Region resource.

To decrease latency for this method, you can optionally omit any unneeded
information from the response by using a field mask. This practice is
especially re..."""
        project = params.get("project")
        if not project:
            return create_gcp_error(
                400,
                "Required field 'project' not found",
                "INVALID_ARGUMENT",
            )
        region_name = params.get("region")
        if not region_name:
            return create_gcp_error(
                400,
                "Required field 'region' not found",
                "INVALID_ARGUMENT",
            )

        region = self.resources.get(region_name)
        if not region:
            return create_gcp_error(
                404,
                f"The resource '{region_name}' was not found",
                "NOT_FOUND",
            )
        return region.to_dict()

    def list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieves the list of region resources available to the specified project.

To decrease latency for this method, you can optionally omit any unneeded
information from the response by using a field ..."""
        project = params.get("project")
        if not project:
            return create_gcp_error(
                400,
                "Required field 'project' not found",
                "INVALID_ARGUMENT",
            )

        resources = list(self.resources.values())
        filter_expr = params.get("filter", "")
        if filter_expr:
            match = re.match(r'name\s*=\s*"?([^"\s]+)"?', filter_expr)
            if match:
                resources = [r for r in resources if r.name == match.group(1)]
        return {
            "kind": "compute#regionList",
            "id": f"projects/{project}/regions",
            "items": [r.to_dict() for r in resources],
            "selfLink": "",
        }


class region_RequestParser:
    @staticmethod
    def parse_request(
        method_name: str,
        path_params: Dict[str, Any],
        query_params: Dict[str, Any],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge path, query, and body params into a flat dict for the backend."""
        parsers = {
            'get': region_RequestParser._parse_get,
            'list': region_RequestParser._parse_list,
        }
        parser = parsers.get(method_name)
        if parser is None:
            raise ValueError(f"Unknown method: {method_name}")
        return parser(path_params, query_params, body)

    @staticmethod
    def _parse_get(
        path_params: Dict[str, Any],
        query_params: Dict[str, Any],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        # Path params
        params.update(path_params)
        # Query params
        params.update(query_params)
        return params

    @staticmethod
    def _parse_list(
        path_params: Dict[str, Any],
        query_params: Dict[str, Any],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        # Path params
        params.update(path_params)
        # Query params
        if 'filter' in query_params:
            params['filter'] = query_params['filter']
        if 'maxResults' in query_params:
            params['maxResults'] = query_params['maxResults']
        if 'orderBy' in query_params:
            params['orderBy'] = query_params['orderBy']
        if 'pageToken' in query_params:
            params['pageToken'] = query_params['pageToken']
        if 'returnPartialSuccess' in query_params:
            params['returnPartialSuccess'] = query_params['returnPartialSuccess']
        return params


class region_ResponseSerializer:
    @staticmethod
    def serialize(
        method_name: str,
        data: Dict[str, Any],
        request_id: str,
    ) -> str:
        if is_error_response(data):
            from ..utils import serialize_gcp_error
            return serialize_gcp_error(data)
        serializers = {
            'get': region_ResponseSerializer._serialize_get,
            'list': region_ResponseSerializer._serialize_list,
        }
        fn = serializers.get(method_name)
        if fn is None:
            return _json.dumps(data)
        return fn(data)

    @staticmethod
    def _serialize_get(data: Dict[str, Any]) -> str:
        return _json.dumps(data)

    @staticmethod
    def _serialize_list(data: Dict[str, Any]) -> str:
        return _json.dumps(data)

