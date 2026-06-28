"""Thin HTTP wrapper around Ollama. Avoids forcing a heavy SDK dependency."""
from __future__ import annotations

import json
import urllib.request
from typing import Iterable, List


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 600.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post_json(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise OllamaError(f"POST {path} failed: {exc}") from exc

    def list_models(self) -> List[str]:
        req = urllib.request.Request(self.base_url + "/api/tags")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise OllamaError(f"GET /api/tags failed: {exc}") from exc
        return [m["name"] for m in data.get("models", [])]

    def generate(self, model: str, prompt: str, *, system: str = "", temperature: float = 0.2,
                 num_predict: int = 1024) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        }
        if system:
            payload["system"] = system
        data = self._post_json("/api/generate", payload)
        return data.get("response", "")

    def embed(self, model: str, texts: Iterable[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for t in texts:
            data = self._post_json("/api/embeddings", {"model": model, "prompt": t})
            emb = data.get("embedding")
            if not emb:
                raise OllamaError(f"empty embedding for model {model}")
            out.append(emb)
        return out
