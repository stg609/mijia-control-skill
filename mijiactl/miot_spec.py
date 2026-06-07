from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Callable


BASE_URL = "https://miot-spec.org/miot-spec-v2"


def fetch_model_spec(model: str, fetch_json: Callable[[str], dict[str, Any]] | None = None) -> dict[str, Any]:
    fetch = fetch_json or _fetch_json
    instances = fetch(f"{BASE_URL}/instances?status=all").get("instances", [])
    match = next((item for item in instances if item.get("model") == model), None)
    if not match:
        raise ValueError(f"model '{model}' was not found in MIoT spec instances")
    spec_type = match["type"]
    instance = fetch(f"{BASE_URL}/instance?type={urllib.parse.quote(spec_type, safe='')}")
    instance["model"] = model
    return instance


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "mijiactl/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
