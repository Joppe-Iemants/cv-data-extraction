"""HTTP transport for the Ollama chat endpoint."""
import json
from urllib.request import Request, urlopen


def chat(endpoint: str, payload: dict, timeout_seconds: int) -> str:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8")
