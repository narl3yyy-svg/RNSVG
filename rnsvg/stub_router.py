"""aiohttp route handlers for the RNSVG stub API and static frontend."""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiohttp import web

from rnsvg.config import AppConfig
from rnsvg.responses import (
    announce_response,
    api_catchall_payload,
    api_status,
    app_info_envelope,
    auth_status,
    blocked_destinations,
    config_envelope,
    csrf_token_response,
    identities_response,
    keyboard_shortcuts_response,
    lxmf_conversation_pins,
    lxmf_conversations,
    lxmf_folders,
    notifications_response,
    post_ok,
    propagation_node_status,
    telephone_ringtone_status,
    telephone_status,
    websocket_config_message,
    websocket_pong,
)
from rnsvg.rns_transport import RNSTransport


@dataclass
class AppState:
    config: AppConfig
    transport: RNSTransport
    public_dir: Path
    config_overrides: dict[str, Any] = field(default_factory=dict)
    csrf_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def public_dir_path() -> Path:
    return repo_root() / "meshchatx" / "public"


def create_app(state: AppState) -> web.Application:
    app = web.Application()
    app["state"] = state
    app.router.add_routes(_build_routes(state))
    return app


def _build_routes(state: AppState) -> list[web.AbstractRouteDef]:
    routes = [
        web.get("/api/v1/auth/status", _handle_auth_status),
        web.get("/api/v1/app/info", _handle_app_info),
        web.get("/api/v1/config", _handle_config_get),
        web.patch("/api/v1/config", _handle_config_patch),
        web.get("/api/v1/status", _handle_status),
        web.get("/api/v1/blocked-destinations", _handle_blocked_destinations),
        web.get("/api/v1/announce", _handle_announce),
        web.get("/api/v1/notifications", _handle_notifications),
        web.get("/api/v1/identities", _handle_identities),
        web.get("/api/v1/lxmf/conversations", _handle_lxmf_conversations),
        web.get("/api/v1/lxmf/conversation-pins", _handle_lxmf_conversation_pins),
        web.get("/api/v1/lxmf/folders", _handle_lxmf_folders),
        web.get("/api/v1/lxmf/propagation-node/status", _handle_propagation_node_status),
        web.get("/api/v1/telephone/status", _handle_telephone_status),
        web.get("/api/v1/telephone/ringtones/status", _handle_telephone_ringtone_status),
        web.get("/api/v1/csrf-token", _handle_csrf_token),
        web.get("/api/v1/auth/csrf", _handle_csrf_token),
        web.post("/api/v1/{tail:.*}", _handle_post_stub),
        web.route("*", "/api/v1/{tail:.*}", _handle_api_catchall),
        web.get("/ws", _handle_websocket),
        web.get("/", _handle_index),
        web.get("/manifest.json", _handle_manifest),
        web.get("/service-worker.js", _handle_service_worker),
    ]

    public_dir = state.public_dir
    if public_dir.is_dir():
        routes.append(
            web.static("/", public_dir, name="static", follow_symlinks=True),
        )

    return routes


def _get_state(request: web.Request) -> AppState:
    return request.app["state"]


async def _handle_auth_status(_request: web.Request) -> web.Response:
    return web.json_response(auth_status())


async def _handle_app_info(request: web.Request) -> web.Response:
    state = _get_state(request)
    return web.json_response(app_info_envelope(state.config, state.transport))


async def _handle_config_get(request: web.Request) -> web.Response:
    state = _get_state(request)
    return web.json_response(config_envelope(state.transport, state.config_overrides))


async def _handle_config_patch(request: web.Request) -> web.Response:
    state = _get_state(request)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"message": "invalid json"}, status=400)
    if not isinstance(data, dict):
        return web.json_response({"message": "invalid request body"}, status=400)
    state.config_overrides.update(data)
    return web.json_response(config_envelope(state.transport, state.config_overrides))


async def _handle_status(_request: web.Request) -> web.Response:
    return web.json_response(api_status())


async def _handle_blocked_destinations(_request: web.Request) -> web.Response:
    return web.json_response(blocked_destinations())


async def _handle_announce(_request: web.Request) -> web.Response:
    return web.json_response(announce_response())


async def _handle_notifications(_request: web.Request) -> web.Response:
    return web.json_response(notifications_response())


async def _handle_identities(request: web.Request) -> web.Response:
    state = _get_state(request)
    return web.json_response(identities_response(state.transport))


async def _handle_lxmf_conversations(_request: web.Request) -> web.Response:
    return web.json_response(lxmf_conversations())


async def _handle_lxmf_conversation_pins(_request: web.Request) -> web.Response:
    return web.json_response(lxmf_conversation_pins())


async def _handle_lxmf_folders(_request: web.Request) -> web.Response:
    return web.json_response(lxmf_folders())


async def _handle_propagation_node_status(_request: web.Request) -> web.Response:
    return web.json_response(propagation_node_status())


async def _handle_telephone_status(_request: web.Request) -> web.Response:
    return web.json_response(telephone_status())


async def _handle_telephone_ringtone_status(_request: web.Request) -> web.Response:
    return web.json_response(telephone_ringtone_status())


async def _handle_csrf_token(request: web.Request) -> web.Response:
    state = _get_state(request)
    return web.json_response(csrf_token_response(state.csrf_token))


async def _handle_post_stub(_request: web.Request) -> web.Response:
    return web.json_response(post_ok())


async def _handle_api_catchall(request: web.Request) -> web.Response:
    payload = api_catchall_payload(request.path, request.method)
    if isinstance(payload, list):
        return web.json_response(payload)
    return web.json_response(payload)


async def _handle_websocket(request: web.Request) -> web.WebSocketResponse:
    state = _get_state(request)
    ws = web.WebSocketResponse(max_msg_size=50 * 1024 * 1024)
    await ws.prepare(request)

    await ws.send_str(
        json.dumps(websocket_config_message(state.transport, state.config_overrides)),
    )

    async for msg in ws:
        if msg.type != web.WSMsgType.TEXT:
            if msg.type == web.WSMsgType.ERROR:
                print(f"WebSocket error: {ws.exception()}")
            continue
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        msg_type = data.get("type")
        if msg_type == "ping":
            await ws.send_str(json.dumps(websocket_pong()))
        elif msg_type == "keyboard_shortcuts.get":
            await ws.send_str(json.dumps(keyboard_shortcuts_response()))

    return ws


async def _handle_index(request: web.Request) -> web.Response:
    state = _get_state(request)
    index_path = state.public_dir / "index.html"
    if not index_path.is_file():
        return web.Response(
            text=_frontend_missing_html(),
            content_type="text/html",
            status=500,
        )
    return web.FileResponse(
        path=index_path,
        headers={"Cache-Control": "no-cache, no-store"},
    )


async def _handle_manifest(request: web.Request) -> web.Response:
    state = _get_state(request)
    manifest_path = state.public_dir / "manifest.json"
    if not manifest_path.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(manifest_path)


async def _handle_service_worker(request: web.Request) -> web.Response:
    state = _get_state(request)
    sw_path = state.public_dir / "service-worker.js"
    if not sw_path.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(sw_path)


def _frontend_missing_html() -> str:
    return """
    <html>
        <head><title>RNSVG - Frontend Missing</title></head>
        <body style="font-family: sans-serif; padding: 2rem; line-height: 1.5; background: #0f172a; color: #f8fafc;">
            <h1 style="color: #38bdf8;">Frontend Missing</h1>
            <p>The MeshChatX web interface files were not found in <code>meshchatx/public</code>.</p>
            <p>Build the frontend first:</p>
            <pre style="background: #1e293b; padding: 1rem; border-radius: 4px; color: #e2e8f0; border: 1px solid #334155;">pnpm install && pnpm run build-frontend</pre>
        </body>
    </html>
    """