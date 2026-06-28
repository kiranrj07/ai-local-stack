"""Phoenix/OTEL tracing. Best-effort — no-op if Phoenix isn't running.

Phoenix's collector listens on http://localhost:6006. If it's not running,
the OTEL exporter buffers spans and silently drops them.

Usage:
    from core.tracing import setup_tracing, trace_span
    setup_tracing()  # idempotent
    with trace_span("query", question="..."):
        ...

Set AI_LOCAL_STACK_TRACE=0 to disable. Set AI_LOCAL_STACK_TRACE=1 to force-attempt.
By default we attempt only when Phoenix is reachable.
"""
from __future__ import annotations

import os
import socket
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Optional


_INITIALIZED = False
_TRACER = None


def _phoenix_reachable(host: str = "localhost", port: int = 6006, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def setup_tracing(*, force: Optional[bool] = None, project_name: str = "ai-local-stack") -> bool:
    """Initialize Phoenix tracing. Returns True if active, False if no-op."""
    global _INITIALIZED, _TRACER
    if _INITIALIZED:
        return _TRACER is not None

    env = os.environ.get("AI_LOCAL_STACK_TRACE", "auto")
    if force is False or env == "0":
        _INITIALIZED = True
        return False
    if force is None and env == "auto":
        if not _phoenix_reachable():
            _INITIALIZED = True
            return False

    try:
        from phoenix.otel import register
        tp = register(
            project_name=project_name,
            endpoint="http://localhost:6006/v1/traces",
            batch=True,
            verbose=False,
        )
        from opentelemetry import trace
        _TRACER = trace.get_tracer("ai-local-stack")
        _INITIALIZED = True
        return True
    except Exception:
        _INITIALIZED = True
        return False


@contextmanager
def trace_span(name: str, **attributes):
    """Start a span if tracing is set up; otherwise just yield."""
    if _TRACER is None:
        yield None
        return
    with _TRACER.start_as_current_span(name) as span:
        for k, v in attributes.items():
            try:
                span.set_attribute(k, v if isinstance(v, (str, int, float, bool)) else str(v))
            except Exception:
                pass
        yield span
