from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, unquote, urlsplit

from .authority_web_api import dispatch_authority_web_api
from .environment import DB_FILE_NAME, ENV_DIR_NAME, discover
from .product_actions import create_monitor, create_project, refresh_monitor, refresh_project_monitors, run_due_monitors
from .monitor_provider_manifest import load_monitor_provider_registry
from .product_service import TestamurProductService

WEB_ROOT = Path(__file__).with_name("web")

_STATIC_ASSETS = {"index.html", "app.js", "styles.css", "authority.js", "authority.css", "authority_reason_groups.js", "authority_constraint_semantics.js"}
_SPA_PREFIXES = {"app", "object", "compare", "impact", "temporal", "projects", "explore", "monitoring", "status", "authority"}
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}
_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'self'; form-action 'self'; "
        "img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
_MAX_JSON_BODY = 64 * 1024


def _json(payload: Mapping[str, Any], *, status: int | None = None) -> dict[str, Any]:
    if status is None:
        status = _status_for_payload(payload)
    return {"status": int(status), "headers": {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", **_SECURITY_HEADERS}, "body": dict(payload)}


def _error(code: str, message: str, *, status: int = 400) -> dict[str, Any]:
    return _json({"ok": False, "schema": "testamur.error.v1", "error": {"code": code, "message": message}}, status=status)


def _status_for_payload(payload: Mapping[str, Any]) -> int:
    if payload.get("ok") is True: return int(HTTPStatus.OK)
    error = payload.get("error"); code = str(error.get("code") if isinstance(error, Mapping) else "")
    if code == "object_not_found": return int(HTTPStatus.NOT_FOUND)
    if code.endswith("capability_unavailable"): return int(HTTPStatus.SERVICE_UNAVAILABLE)
    if code in {"incompatible_compare", "compare_not_supported", "history_not_supported"}: return int(HTTPStatus.UNPROCESSABLE_ENTITY)
    return int(HTTPStatus.BAD_REQUEST)


def _one(query: Mapping[str, list[str]], name: str, *, required: bool = True) -> str | None:
    values = query.get(name) or []
    if not values:
        if required: raise ValueError(f"missing required query parameter: {name}")
        return None
    if len(values) != 1 or not values[0].strip(): raise ValueError(f"query parameter {name} must occur exactly once and be non-empty")
    return values[0].strip()


def _limit(query: Mapping[str, list[str]], *, default: int = 50, maximum: int = 500) -> int:
    raw = _one(query, "limit", required=False)
    if raw is None: return default
    try: value = int(raw)
    except ValueError as exc: raise ValueError("limit must be an integer") from exc
    if value < 1 or value > maximum: raise ValueError(f"limit must be between 1 and {maximum}")
    return value


def _temporal_query(query: Mapping[str, list[str]]) -> dict[str, Any]:
    clauses: list[dict[str, str]] = []; allowed = {"known_at", "available_by", "effective_at"}
    for raw in query.get("clause") or []:
        mode, separator, at = raw.partition("="); normalized = mode.strip().lower()
        if not separator or normalized not in allowed or not at.strip(): raise ValueError("clause must be MODE=TIME with MODE one of KNOWN_AT, AVAILABLE_BY, EFFECTIVE_AT")
        clauses.append({"mode": normalized, "at": at.strip()})
    if not clauses: raise ValueError("at least one temporal clause is required")
    return {"clauses": clauses, "perspective": _one(query, "perspective", required=False), "limit": _limit(query, default=100)}


def dispatch_api(service: TestamurProductService, target: str) -> dict[str, Any]:
    try:
        authority = dispatch_authority_web_api(service, target)
        if authority is not None: return _json(authority)
    except ValueError as exc: return _error("invalid_argument", str(exc))
    split = urlsplit(target); path = split.path.rstrip("/") or "/"; query = parse_qs(split.query, keep_blank_values=True)
    try:
        if path == "/v1/status":
            if query: raise ValueError("status accepts no query parameters")
            return _json(service.status())
        if path == "/v1/dashboard":
            unknown = set(query) - {"limit"}
            if unknown: raise ValueError(f"dashboard does not accept query parameters: {', '.join(sorted(unknown))}")
            return _json(service.dashboard(limit=_limit(query, default=30, maximum=100)))
        if path == "/v1/project":
            unknown = set(query) - {"ref"}
            if unknown: raise ValueError(f"project does not accept query parameters: {', '.join(sorted(unknown))}")
            return _json(service.project(_one(query, "ref") or ""))
        if path == "/v1/object": return _json(service.get_object(_one(query, "ref") or ""))
        if path == "/v1/history": return _json(service.history(_one(query, "ref") or "", limit=_limit(query)))
        if path == "/v1/compare": return _json(service.compare(_one(query, "left") or "", _one(query, "right") or ""))
        if path == "/v1/impact": return _json(service.impact(_one(query, "ref") or ""))
        if path == "/v1/temporal": return _json(service.temporal(_one(query, "ref") or "", _temporal_query(query)))
        if path == "/v1/temporal-events": return _json(service.temporal_events(_one(query, "ref") or "", {"event_kinds": query.get("event_kind") or None, "recorded_by": _one(query, "recorded_by", required=False), "event_time_by": _one(query, "event_time_by", required=False), "perspective": _one(query, "perspective", required=False), "limit": _limit(query, default=100)}))
    except ValueError as exc: return _error("invalid_argument", str(exc))
    return _error("route_not_found", "unknown Testamur API route", status=404)


def dispatch_api_write(service: TestamurProductService, target: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    split = urlsplit(target); path = split.path.rstrip("/") or "/"
    if split.query: return _error("invalid_argument", "write routes do not accept query parameters")
    try:
        if path == "/v1/projects/refresh":
            unknown = set(payload) - {"project_ref"}
            if unknown: raise ValueError(f"project refresh does not accept fields: {', '.join(sorted(unknown))}")
            project_ref = str(payload.get("project_ref") or "").strip()
            if not project_ref: raise ValueError("project_ref is required")
            return _json(refresh_project_monitors(service, project_ref))
        if path == "/v1/monitors/refresh":
            unknown = set(payload) - {"monitor_ref"}
            if unknown: raise ValueError(f"monitor refresh does not accept fields: {', '.join(sorted(unknown))}")
            monitor_ref = str(payload.get("monitor_ref") or "").strip()
            if not monitor_ref: raise ValueError("monitor_ref is required")
            return _json(refresh_monitor(service, monitor_ref))
        if path == "/v1/monitors/run-due":
            unknown = set(payload) - {"limit"}
            if unknown: raise ValueError(f"run-due does not accept fields: {', '.join(sorted(unknown))}")
            return _json(run_due_monitors(service, limit=int(payload.get("limit") or 20)))
        if path == "/v1/projects": return _json(create_project(service, payload))
        if path == "/v1/monitors": return _json(create_monitor(service, payload))
    except (ValueError, TypeError) as exc: return _error("invalid_argument", str(exc))
    return _error("route_not_found", "unknown Testamur API write route", status=404)


def dispatch_web_get(target: str) -> dict[str, Any]:
    split = urlsplit(target); path = unquote(split.path)
    if split.query: return _error("invalid_argument", "static routes do not accept query parameters")
    name = path.lstrip("/") or "index.html"
    if name in _STATIC_ASSETS:
        file_path = WEB_ROOT / name
    elif name.split("/", 1)[0] in _SPA_PREFIXES:
        file_path = WEB_ROOT / "index.html"
    else:
        return _error("route_not_found", "unknown Testamur web route", status=404)
    if not file_path.is_file(): return _error("asset_not_found", "web asset unavailable", status=404)
    return {"status": 200, "headers": {"Content-Type": _CONTENT_TYPES.get(file_path.suffix, "application/octet-stream"), **_SECURITY_HEADERS}, "body": file_path.read_bytes()}


def _service_from_root(root: Path | None = None) -> TestamurProductService:
    env = discover(root)
    return TestamurProductService(env / DB_FILE_NAME)


def create_server(host: str = "127.0.0.1", port: int = 8765, *, root: Path | None = None) -> ThreadingHTTPServer:
    service = _service_from_root(root)
    class Handler(BaseHTTPRequestHandler):
        def _send(self, result: Mapping[str, Any]) -> None:
            status = int(result["status"]); body = result["body"]
            if isinstance(body, Mapping): raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, bytes): raw = body
            else: raw = str(body).encode("utf-8")
            self.send_response(status)
            for key, value in result.get("headers", {}).items(): self.send_header(str(key), str(value))
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def do_GET(self) -> None:
            result = dispatch_api(service, self.path) if self.path.startswith("/v1/") else dispatch_web_get(self.path)
            self._send(result)
        def do_POST(self) -> None:
            if not self.path.startswith("/v1/"): self._send(_error("method_not_allowed", "POST is only supported for API routes", status=405)); return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length > _MAX_JSON_BODY: self._send(_error("payload_too_large", "request body exceeds limit", status=413)); return
                raw = self.rfile.read(length); payload = json.loads(raw or b"{}")
                if not isinstance(payload, Mapping): raise ValueError("JSON body must be an object")
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(_error("invalid_json", str(exc))); return
            self._send(dispatch_api_write(service, self.path, payload))
        def log_message(self, format: str, *args: object) -> None:
            if os.environ.get("TESTAMUR_WEB_LOG"): super().log_message(format, *args)
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="testamur-web")
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8765); parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    server = create_server(args.host, args.port, root=args.root)
    print(f"Testamur web: http://{args.host}:{args.port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__ == "__main__": raise SystemExit(main())
