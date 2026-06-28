"""Mode router.

Reads config/system.yaml and answers:
  - which mode to use (auto | local | hybrid)?
  - which Ollama URL to use?
  - is the active endpoint actually reachable?
  - should we fall back to local?

Modes:
  - "auto"   : probe hybrid first (opening an SSH tunnel if configured), use it if
               reachable; otherwise silently use local. RECOMMENDED.
  - "local"  : Mac Ollama only.
  - "hybrid" : Force hybrid; if unreachable, fall back to local only when
               fallback.enabled (default true), else raise.

Used by every Python script that needs an LLM/embedding endpoint.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_YAML = PROJECT_ROOT / "config" / "system.yaml"


@dataclass
class Endpoint:
    mode: str                  # actual mode after fallback resolution: "local" | "hybrid"
    requested_mode: str        # "auto" | "local" | "hybrid"
    ollama_url: str
    llm_model: str
    embedding_provider: str
    embedding_model: str
    reranker_enabled: bool
    reranker_model: str
    fell_back: bool            # True if hybrid was requested/attempted but local was used
    reason: str                # human-readable explanation


def load_system_config(path: Path = SYSTEM_YAML) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"system.yaml not found at {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _ollama_reachable(url: str, timeout: float = 4.0) -> bool:
    """GET {url}/api/tags. True iff HTTP 200."""
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/tags")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError):
        return False


def _port_listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _hybrid_endpoint_url(hybrid_cfg: Dict[str, Any]) -> str:
    if hybrid_cfg.get("connection_type") == "direct_lan":
        return hybrid_cfg.get("direct_lan_url", hybrid_cfg["ollama_url"])
    return hybrid_cfg["ollama_url"]


def _try_open_tunnel(hybrid_cfg: Dict[str, Any], log_fn=lambda _: None) -> bool:
    """If hybrid uses ssh_tunnel and the local port isn't listening, try to open it.

    Returns True if the tunnel is up after the attempt, False otherwise. Best-effort:
    on any error we return False so the caller falls back to local.
    """
    if hybrid_cfg.get("connection_type") != "ssh_tunnel":
        return False
    port = int(hybrid_cfg.get("ssh_tunnel_local_port", 11435))
    if _port_listening(port):
        return _ollama_reachable(f"http://localhost:{port}", timeout=2.0)

    # Attempt to start the tunnel script (best effort).
    ssh = shutil.which("ssh")
    if not ssh:
        log_fn("ssh binary not found; skipping auto-tunnel")
        return False

    user = hybrid_cfg.get("remote_user") or "REPLACE_ME_USER"
    ip = hybrid_cfg.get("remote_ip") or "REPLACE_ME_WORKER_LAN_IP"
    cmd = [
        ssh, "-f", "-N",
        "-o", "ConnectTimeout=4",
        "-o", "BatchMode=yes",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "-L", f"{port}:localhost:11434",
        f"{user}@{ip}",
    ]
    log_fn(f"opening ssh tunnel: ssh -L {port}:localhost:11434 {user}@{ip}")
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=6)
        if proc.returncode != 0:
            log_fn(f"tunnel failed rc={proc.returncode}: {proc.stderr.decode(errors='replace').strip()}")
            return False
    except (subprocess.TimeoutExpired, OSError) as exc:
        log_fn(f"tunnel attempt error: {exc}")
        return False

    # Give the listener a moment to come up.
    for _ in range(8):
        if _ollama_reachable(f"http://localhost:{port}", timeout=1.0):
            return True
        time.sleep(0.25)
    return False


def _endpoint_from_local(cfg: Dict[str, Any], *, requested: str,
                         fell_back: bool, reason: str) -> Endpoint:
    loc = cfg["local"]
    return Endpoint(
        mode="local",
        requested_mode=requested,
        ollama_url=loc["ollama_url"],
        llm_model=loc["llm_model"],
        embedding_provider=loc["embedding_provider"],
        embedding_model=loc["embedding_model"],
        reranker_enabled=loc.get("reranker_enabled", False),
        reranker_model=loc.get("reranker_model", ""),
        fell_back=fell_back,
        reason=reason,
    )


def _endpoint_from_hybrid(cfg: Dict[str, Any], *, requested: str, url: str,
                          reason: str) -> Endpoint:
    hyb = cfg["hybrid"]
    return Endpoint(
        mode="hybrid",
        requested_mode=requested,
        ollama_url=url,
        llm_model=hyb["llm_model"],
        embedding_provider=hyb["embedding_provider"],
        embedding_model=hyb["embedding_model"],
        reranker_enabled=hyb.get("reranker_enabled", False),
        reranker_model=hyb.get("reranker_model", ""),
        fell_back=False,
        reason=reason,
    )


def resolve_endpoint(config: Optional[Dict[str, Any]] = None, *,
                     verbose: bool = False) -> Endpoint:
    """Return the Endpoint to use, applying auto/fallback rules from system.yaml.

    `verbose=True` prints probe steps to stderr (helpful when debugging).
    """
    cfg = config or load_system_config()
    requested = cfg.get("mode", "auto")
    log = (lambda msg: print(f"[router] {msg}", file=sys.stderr)) if verbose else (lambda _msg: None)
    fb_cfg = cfg.get("fallback", {})
    http_timeout = fb_cfg.get("http_timeout_seconds", 4)

    # --- forced local
    if requested == "local":
        loc = cfg["local"]
        reachable = _ollama_reachable(loc["ollama_url"], http_timeout)
        reason = "local mode" if reachable else "local mode (WARN: Ollama not reachable)"
        return _endpoint_from_local(cfg, requested="local", fell_back=False, reason=reason)

    # --- auto or forced hybrid: try the hybrid endpoint
    hyb = cfg["hybrid"]
    hybrid_url = _hybrid_endpoint_url(hyb)

    # If ssh_tunnel mode and not reachable yet, try to bring tunnel up automatically.
    if not _ollama_reachable(hybrid_url, http_timeout):
        log(f"hybrid endpoint {hybrid_url} not reachable; attempting auto-tunnel")
        _try_open_tunnel(hyb, log_fn=log)

    if _ollama_reachable(hybrid_url, http_timeout):
        log(f"using hybrid endpoint {hybrid_url}")
        prefix = "auto -> hybrid" if requested == "auto" else "hybrid mode"
        return _endpoint_from_hybrid(cfg, requested=requested, url=hybrid_url,
                                     reason=f"{prefix} via {hybrid_url}")

    # Hybrid unreachable
    if requested == "auto":
        log("hybrid unreachable; using local")
        return _endpoint_from_local(
            cfg, requested="auto", fell_back=True,
            reason=f"auto: hybrid endpoint {hybrid_url} unreachable; using local",
        )

    # requested == "hybrid"
    if fb_cfg.get("enabled", True) and fb_cfg.get("if_remote_unreachable_use_local", True):
        log("hybrid unreachable; falling back to local (fallback enabled)")
        return _endpoint_from_local(
            cfg, requested="hybrid", fell_back=True,
            reason=f"hybrid endpoint {hybrid_url} unreachable; fell back to local",
        )
    raise RuntimeError(
        f"hybrid mode requested but {hybrid_url} unreachable and fallback disabled"
    )


def print_status(verbose: bool = False) -> None:
    cfg = load_system_config()
    ep = resolve_endpoint(cfg, verbose=verbose)
    print(f"requested mode : {ep.requested_mode}")
    print(f"active mode    : {ep.mode}{' (fell back)' if ep.fell_back else ''}")
    print(f"ollama url     : {ep.ollama_url}")
    print(f"llm model      : {ep.llm_model}")
    print(f"embedding      : {ep.embedding_provider}:{ep.embedding_model}")
    print(f"reranker       : {'on (' + ep.reranker_model + ')' if ep.reranker_enabled else 'off'}")
    print(f"reason         : {ep.reason}")


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    print_status(verbose=verbose)
