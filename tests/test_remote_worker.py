"""Connectivity test for the Ubuntu worker.

In local mode, this test no-ops with a printed skip message.
In hybrid mode, it verifies the configured Ollama endpoint responds.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.router import load_system_config, resolve_endpoint
import urllib.request, urllib.error


def test_remote_endpoint_or_skip():
    cfg = load_system_config()
    if cfg.get("mode") != "hybrid":
        print("skip: not in hybrid mode")
        return
    ep = resolve_endpoint(cfg)
    url = ep.ollama_url.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.status == 200
    except Exception as exc:
        raise AssertionError(f"remote endpoint {url} unreachable: {exc}")


if __name__ == "__main__":
    test_remote_endpoint_or_skip()
    print("test_remote_worker OK")
