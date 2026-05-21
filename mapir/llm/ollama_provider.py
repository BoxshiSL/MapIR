"""Ollama provider — talks to a local Ollama daemon over HTTP via stdlib urllib.

No third-party HTTP client is required. The daemon must already be running
locally (e.g. via the Ollama desktop installer) and the user must have pulled
the model themselves with `ollama pull <model>`. We never auto-download.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .providers import LLMJsonRequest, LLMJsonResponse
from .settings import DEFAULT_BASE_URL


def _normalise_base_url(url: str) -> str:
    return url.rstrip("/")


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = 120,
        structured_output: bool = True,
    ) -> None:
        self.base_url = _normalise_base_url(base_url)
        self.timeout_seconds = timeout_seconds
        self.structured_output = structured_output

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        try:
            self._http_get("/api/tags", timeout=min(5, self.timeout_seconds))
            return True
        except Exception:  # noqa: BLE001 — any failure is "not available"
            return False

    def list_models(self) -> list[str]:
        try:
            body = self._http_get("/api/tags", timeout=min(10, self.timeout_seconds))
        except Exception:  # noqa: BLE001
            return []
        models: list[str] = []
        for entry in body.get("models", []) or []:
            name = entry.get("name") or entry.get("model")
            if isinstance(name, str):
                models.append(name)
        return sorted(set(models))

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_json(self, request: LLMJsonRequest) -> LLMJsonResponse:
        model = request.model or ""
        if not model:
            return LLMJsonResponse(
                ok=False,
                raw_text="",
                json_data=None,
                error="OllamaProvider requires a model name (e.g. 'qwen3:8b')",
                provider_name=self.name,
                model_name=None,
                elapsed_ms=0,
            )

        # Force JSON via system message regardless of structured_output, so models
        # that ignore `format` still emit JSON.
        system = (
            request.system_prompt.rstrip()
            + "\n\nIMPORTANT: respond with strict JSON only. No Markdown, no commentary."
        )

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": request.user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if self.structured_output and request.schema is not None:
            payload["format"] = request.schema
        else:
            payload["format"] = "json"

        start = time.perf_counter()
        try:
            body = self._http_post("/api/chat", payload, timeout=self.timeout_seconds)
        except urllib.error.HTTPError as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            return LLMJsonResponse(
                ok=False,
                raw_text="",
                json_data=None,
                error=_format_http_error(exc, model, self.base_url),
                provider_name=self.name,
                model_name=model,
                elapsed_ms=elapsed,
            )
        except urllib.error.URLError as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            return LLMJsonResponse(
                ok=False,
                raw_text="",
                json_data=None,
                error=f"Cannot reach Ollama at {self.base_url}: {exc.reason}",
                provider_name=self.name,
                model_name=model,
                elapsed_ms=elapsed,
            )
        except TimeoutError:
            elapsed = int((time.perf_counter() - start) * 1000)
            return LLMJsonResponse(
                ok=False,
                raw_text="",
                json_data=None,
                error=f"Ollama timed out after {self.timeout_seconds}s",
                provider_name=self.name,
                model_name=model,
                elapsed_ms=elapsed,
            )
        elapsed = int((time.perf_counter() - start) * 1000)

        raw_text = ""
        if isinstance(body, dict):
            msg = body.get("message")
            if isinstance(msg, dict):
                raw_text = str(msg.get("content", "") or "")
            if not raw_text:
                raw_text = str(body.get("response", "") or "")

        json_data, parse_err = _try_parse_json(raw_text)
        if json_data is None:
            return LLMJsonResponse(
                ok=False,
                raw_text=raw_text,
                json_data=None,
                error=f"Model did not return valid JSON: {parse_err}",
                provider_name=self.name,
                model_name=model,
                elapsed_ms=elapsed,
            )

        return LLMJsonResponse(
            ok=True,
            raw_text=raw_text,
            json_data=json_data,
            error=None,
            provider_name=self.name,
            model_name=model,
            elapsed_ms=elapsed,
        )

    # ------------------------------------------------------------------
    # HTTP helpers (stdlib only)
    # ------------------------------------------------------------------

    def _http_get(self, path: str, timeout: float) -> dict[str, Any]:
        req = urllib.request.Request(self.base_url + path, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data) if data else {}

    def _http_post(self, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data) if data else {}


def _try_parse_json(text: str) -> tuple[dict[str, Any] | None, str | None]:
    if not text or not text.strip():
        return None, "empty response"
    # Some models emit fenced JSON despite instructions — strip a leading fence.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # drop opening fence (```json or ```)
        nl = cleaned.find("\n")
        if nl != -1:
            cleaned = cleaned[nl + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "top-level JSON is not an object"
    return data, None


def _format_http_error(exc: urllib.error.HTTPError, model: str, base_url: str) -> str:
    detail = ""
    try:
        body = exc.read().decode("utf-8")
        if body:
            detail = f" — {body[:200]}"
    except Exception:  # noqa: BLE001
        pass
    if exc.code == 404:
        return f"Model {model!r} not found at {base_url}. " f"Run: ollama pull {model}{detail}"
    return f"Ollama HTTP {exc.code} {exc.reason}{detail}"
