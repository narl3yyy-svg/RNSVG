"""aiohttp route handlers for RNSVG API and static frontend."""

from __future__ import annotations

import io
import json
import secrets
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aiohttp import web

from rnsvg.config import AppConfig
from rnsvg.discovery import ASPECT_API_ALIASES
from rnsvg.responses import (
    announce_response,
    announces_response,
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
    lxmf_conversations_response,
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
from rnsvg.websocket_hub import WebSocketHub


@dataclass
class AppState:
    config: AppConfig
    transport: RNSTransport
    public_dir: Path
    websocket_hub: WebSocketHub = field(default_factory=WebSocketHub)
    config_overrides: dict[str, Any] = field(default_factory=dict)
    csrf_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))


def wire_messaging_events(state: AppState) -> None:
    """Connect inbound/outbound message handlers to the WebSocket hub."""

    def on_inbound(msg: dict[str, Any], source_hash: str) -> None:
        local = state.transport.node_destination_hash or ""
        records, _ = state.transport.discovery.list_announces(
            aspect="rnsvg.node",
            destination_hash=source_hash,
        )
        name = records[0].display_name if records else source_hash[:8]
        state.websocket_hub.broadcast_json(
            state.transport.messaging.delivery_event(msg, local, name),
        )

    def on_outbound(msg: dict[str, Any]) -> None:
        local = state.transport.node_destination_hash or ""
        state.websocket_hub.broadcast_json(
            state.transport.messaging.created_event(msg, local),
        )

    state.transport.messaging._on_message = on_inbound
    state.transport.messaging._on_outbound = on_outbound


def public_dir_path() -> Path:
    return Path(__file__).resolve().parent.parent / "meshchatx" / "public"


def create_app(state: AppState) -> web.Application:
    app = web.Application(client_max_size=50 * 1024 * 1024)
    app["state"] = state
    app.router.add_routes(_routes(state))
    return app


def _routes(state: AppState) -> list[web.AbstractRouteDef]:
    routes = [
        web.get("/api/v1/auth/status", _auth_status),
        web.get("/api/v1/app/info", _app_info),
        web.post("/api/v1/app/tutorial/seen", _tutorial_seen),
        web.get("/api/v1/app/changelog", _changelog_get),
        web.post("/api/v1/app/changelog/seen", _changelog_seen),
        web.get("/api/v1/config", _config_get),
        web.patch("/api/v1/config", _config_patch),
        web.get("/api/v1/status", _status),
        web.get("/api/v1/blocked-destinations", _blocked),
        web.get("/api/v1/announce", _announce),
        web.get("/api/v1/announces", _announces),
        web.post("/api/v1/announces/query", _announces_query),
        web.get("/api/v1/notifications", _notifications),
        web.get("/api/v1/identities", _identities),
        web.get("/api/v1/identities/export-all", _identities_export),
        web.post("/api/v1/identities/create", _identities_create),
        web.post("/api/v1/identities/switch", _identities_switch),
        web.delete("/api/v1/identities/{identity_hash}", _identities_delete),
        web.get("/api/v1/identity/backup/download", _identity_download),
        web.get("/api/v1/identity/backup/base32", _identity_base32),
        web.post("/api/v1/identity/restore", _identity_restore),
        web.get("/api/v1/reticulum/interfaces", _interfaces_list),
        web.get("/api/v1/reticulum/interfaces/help/{interface_type}", _interface_help),
        web.post("/api/v1/reticulum/interfaces/add", _interfaces_add),
        web.post("/api/v1/reticulum/interfaces/enable", _interfaces_enable),
        web.post("/api/v1/reticulum/interfaces/disable", _interfaces_disable),
        web.post("/api/v1/reticulum/interfaces/delete", _interfaces_delete),
        web.post("/api/v1/reticulum/reload", _reticulum_reload),
        web.get("/api/v1/reticulum/discovered-interfaces", _discovered_interfaces),
        web.get("/api/v1/reticulum/discovery", _discovery_get),
        web.patch("/api/v1/reticulum/discovery", _discovery_patch),
        web.get("/api/v1/community-interfaces", _community_interfaces),
        web.post("/api/v1/community-interfaces/refresh", _ok),
        web.post("/api/v1/setup/storage-migration", _ok),
        web.get("/api/v1/lxmf/conversations", _lxmf_conversations),
        web.get("/api/v1/lxmf/conversation-pins", _lxmf_pins),
        web.get("/api/v1/lxmf/folders", _lxmf_folders),
        web.get("/api/v1/lxmf/propagation-node/status", _propagation_status),
        web.post("/api/v1/lxmf-messages/send", _lxmf_send),
        web.get("/api/v1/lxmf-messages/conversation/{destination_hash}", _lxmf_conversation),
        web.delete("/api/v1/lxmf-messages/conversation/{destination_hash}", _lxmf_delete_conversation),
        web.get("/api/v1/telephone/status", _telephone_status),
        web.get("/api/v1/telephone/call/{identity_hash}", _telephone_call),
        web.get("/api/v1/telephone/hangup", _telephone_hangup),
        web.get("/api/v1/telephone/ringtones/status", _telephone_ringtone),
        web.get("/api/v1/share/status", _share_status),
        web.patch("/api/v1/share", _share_patch),
        web.get("/api/v1/share/files", _share_files),
        web.get("/api/v1/csrf-token", _csrf),
        web.get("/api/v1/auth/csrf", _csrf),
        web.post("/api/v1/{tail:.*}", _ok),
        web.route("*", "/api/v1/{tail:.*}", _catchall),
        web.get("/ws", _websocket),
        web.get("/", _index),
        web.get("/manifest.json", _manifest),
        web.get("/service-worker.js", _service_worker),
    ]
    if state.public_dir.is_dir():
        routes.append(web.static("/", state.public_dir, name="static", follow_symlinks=True))
    return routes


def _state(request: web.Request) -> AppState:
    return request.app["state"]


def _int_query(value: str | None, default: int | None = None) -> int | None:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


async def _auth_status(_: web.Request) -> web.Response:
    return web.json_response(auth_status())


async def _app_info(request: web.Request) -> web.Response:
    s = _state(request)
    return web.json_response(app_info_envelope(s.config, s.transport))


async def _tutorial_seen(request: web.Request) -> web.Response:
    s = _state(request)
    s.config.state.tutorial_seen = True
    s.config.save_state()
    return web.json_response(post_ok())


async def _changelog_get(request: web.Request) -> web.Response:
    import html as html_module

    from rnsvg.version import __version__

    changelog_path = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
    if changelog_path.is_file():
        content = changelog_path.read_text(encoding="utf-8")
    else:
        content = f"# RNSVG {__version__}\n\nSee the project repository for release notes.\n"
    escaped = html_module.escape(content)
    return web.json_response(
        {
            "changelog": content,
            "html": f"<pre class='changelog-pre'>{escaped}</pre>",
            "version": __version__,
        },
    )


async def _changelog_seen(request: web.Request) -> web.Response:
    s = _state(request)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "invalid json"}, status=400)
    version = data.get("version") if isinstance(data, dict) else None
    if not version:
        return web.json_response({"error": "Version required"}, status=400)
    s.config.state.changelog_seen_version = str(version)
    s.config.save_state()
    return web.json_response({"message": f"Changelog version {version} marked as seen"})


async def _config_get(request: web.Request) -> web.Response:
    s = _state(request)
    return web.json_response(config_envelope(s.transport, s.config_overrides))


async def _config_patch(request: web.Request) -> web.Response:
    s = _state(request)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"message": "invalid json"}, status=400)
    if not isinstance(data, dict):
        return web.json_response({"message": "invalid body"}, status=400)
    if isinstance(data.get("display_name"), str):
        s.transport.set_display_name(data["display_name"].strip() or "RNSVG User")
    for key in ("auto_announce_enabled", "auto_announce_interval_seconds", "last_announced_at", "telephone_enabled"):
        if key in data:
            setattr(s.config.state, key, data[key])
    s.config.save_state()
    s.config_overrides.update(data)
    return web.json_response(config_envelope(s.transport, s.config_overrides))


async def _status(_: web.Request) -> web.Response:
    return web.json_response(api_status())


async def _blocked(_: web.Request) -> web.Response:
    return web.json_response(blocked_destinations())


async def _announce(request: web.Request) -> web.Response:
    try:
        _state(request).transport.announce()
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=500)
    return web.json_response(announce_response())


async def _announces(request: web.Request) -> web.Response:
    s = _state(request)
    aspect = request.query.get("aspect")
    if aspect and aspect not in ASPECT_API_ALIASES and aspect != "rnsvg.node":
        return web.json_response({"announces": [], "total_count": 0})
    return web.json_response(
        announces_response(
            s.transport,
            aspect=aspect,
            identity_hash=request.query.get("identity_hash"),
            destination_hash=request.query.get("destination_hash"),
            limit=_int_query(request.query.get("limit")),
            offset=_int_query(request.query.get("offset"), 0) or 0,
        ),
    )


async def _announces_query(request: web.Request) -> web.Response:
    s = _state(request)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        data = {}
    dests = data.get("destination_hashes") if isinstance(data, dict) else None
    if not isinstance(dests, list):
        return web.json_response({"announces": [], "total_count": 0})
    out: list[dict[str, Any]] = []
    for dest in dests:
        payload = announces_response(s.transport, aspect="rnsvg.node", destination_hash=str(dest))
        out.extend(payload["announces"])
    return web.json_response({"announces": out, "total_count": len(out)})


async def _notifications(_: web.Request) -> web.Response:
    return web.json_response(notifications_response())


async def _identities(request: web.Request) -> web.Response:
    return web.json_response(identities_response(_state(request).transport))


async def _identities_create(request: web.Request) -> web.Response:
    s = _state(request)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        data = {}
    try:
        result = s.transport.create_identity(data.get("display_name") if isinstance(data, dict) else None)
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=500)
    return web.json_response({"message": "Identity created successfully", "identity": result})


async def _identities_switch(request: web.Request) -> web.Response:
    s = _state(request)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"message": "invalid json"}, status=400)
    identity_hash = data.get("identity_hash") if isinstance(data, dict) else None
    if not identity_hash:
        return web.json_response({"message": "identity_hash required"}, status=400)
    try:
        s.transport.switch_identity(str(identity_hash))
    except FileNotFoundError:
        return web.json_response({"message": "Identity not found"}, status=404)
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=500)
    return web.json_response(
        {
            "message": "Identity switched successfully.",
            "hotswapped": True,
            "identity_hash": identity_hash,
            "display_name": s.transport.display_name,
        },
    )


async def _identities_delete(request: web.Request) -> web.Response:
    s = _state(request)
    identity_hash = request.match_info["identity_hash"]
    try:
        if not s.transport.delete_identity(identity_hash):
            return web.json_response({"message": "Identity not found"}, status=404)
    except ValueError as exc:
        return web.json_response({"message": str(exc)}, status=400)
    return web.json_response({"message": "Identity deleted successfully"})


async def _identities_export(request: web.Request) -> web.Response:
    all_bytes = _state(request).transport.identity_manager.export_all_bytes()
    if not all_bytes:
        return web.json_response({"message": "No identities"}, status=400)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for h, data in all_bytes.items():
            zf.writestr(f"identity_{h}", data)
    return web.Response(
        body=buf.getvalue(),
        headers={"Content-Type": "application/zip", "Content-Disposition": 'attachment; filename="identities.zip"'},
    )


async def _identity_download(request: web.Request) -> web.Response:
    s = _state(request)
    h = s.transport.current_identity_hash
    if not h:
        return web.json_response({"message": "No identity"}, status=400)
    return web.Response(
        body=s.transport.identity_manager.get_identity_backup_bytes(h),
        headers={"Content-Type": "application/octet-stream", "Content-Disposition": 'attachment; filename="identity"'},
    )


async def _identity_base32(request: web.Request) -> web.Response:
    s = _state(request)
    h = s.transport.current_identity_hash
    if not h:
        return web.json_response({"message": "No identity"}, status=400)
    return web.json_response({"identity_base32": s.transport.identity_manager.get_identity_base32(h)})


async def _identity_restore(request: web.Request) -> web.Response:
    s = _state(request)
    try:
        if "multipart/form-data" in request.headers.get("Content-Type", ""):
            reader = await request.multipart()
            field = await reader.next()
            chunks = []
            while field and field.name != "file":
                field = await reader.next()
            if not field:
                return web.json_response({"message": "file required"}, status=400)
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                chunks.append(chunk)
            display_name = None
            nxt = await reader.next()
            while nxt:
                if nxt.name == "display_name":
                    display_name = (await nxt.text()).strip()
                nxt = await reader.next()
            result = s.transport.restore_identity_from_bytes(b"".join(chunks), display_name)
        else:
            data = await request.json()
            b32 = data.get("base32") if isinstance(data, dict) else None
            if not b32:
                return web.json_response({"message": "base32 required"}, status=400)
            result = s.transport.restore_identity_from_base32(str(b32), data.get("display_name"))
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=500)
    return web.json_response({"message": "Identity restored", "identity": result})


async def _interfaces_list(request: web.Request) -> web.Response:
    return web.json_response({"interfaces": _state(request).transport.interfaces.list_interfaces()})


async def _interface_help(request: web.Request) -> web.Response:
    t = request.match_info["interface_type"]
    return web.json_response({"type": t, "help": _state(request).transport.interfaces.get_help(t)})


async def _interfaces_add(request: web.Request) -> web.Response:
    s = _state(request)
    data = await request.json()
    name = data.get("name")
    iface_type = data.get("type")
    if not name or not iface_type:
        return web.json_response({"message": "name and type required"}, status=400)
    s.transport.interfaces.add_interface(str(name), str(iface_type), data)
    s.transport.reload_reticulum()
    return web.json_response(post_ok())


async def _interfaces_enable(request: web.Request) -> web.Response:
    data = await request.json()
    ok = _state(request).transport.interfaces.set_interface_enabled(data.get("name"), True)
    return web.json_response(post_ok() if ok else {"message": "not found"}, status=200 if ok else 404)


async def _interfaces_disable(request: web.Request) -> web.Response:
    data = await request.json()
    ok = _state(request).transport.interfaces.set_interface_enabled(data.get("name"), False)
    return web.json_response(post_ok() if ok else {"message": "not found"}, status=200 if ok else 404)


async def _interfaces_delete(request: web.Request) -> web.Response:
    data = await request.json()
    ok = _state(request).transport.interfaces.delete_interface(data.get("name"))
    return web.json_response(post_ok() if ok else {"message": "not found"}, status=200 if ok else 404)


async def _reticulum_reload(request: web.Request) -> web.Response:
    _state(request).transport.reload_reticulum()
    return web.json_response({"message": "Reticulum reload acknowledged"})


async def _discovered_interfaces(_: web.Request) -> web.Response:
    return web.json_response({"interfaces": []})


async def _discovery_get(_: web.Request) -> web.Response:
    return web.json_response({"discovery": {"enabled": True, "autoconnect_discovered_interfaces": 0}})


async def _discovery_patch(request: web.Request) -> web.Response:
    await request.json()
    return web.json_response(post_ok())


async def _community_interfaces(_: web.Request) -> web.Response:
    return web.json_response({"interfaces": []})


async def _lxmf_conversations(request: web.Request) -> web.Response:
    return web.json_response(lxmf_conversations_response(_state(request).transport))


async def _lxmf_pins(_: web.Request) -> web.Response:
    return web.json_response(lxmf_conversation_pins())


async def _lxmf_folders(_: web.Request) -> web.Response:
    return web.json_response(lxmf_folders())


async def _propagation_status(_: web.Request) -> web.Response:
    return web.json_response(propagation_node_status())


async def _lxmf_send(request: web.Request) -> web.Response:
    s = _state(request)
    data = await request.json()
    lm = data.get("lxmf_message") if isinstance(data, dict) else None
    if not isinstance(lm, dict):
        return web.json_response({"message": "lxmf_message required"}, status=400)
    try:
        msg = s.transport.messaging.send_text(
            destination_hash=str(lm["destination_hash"]),
            content=str(lm.get("content", "")),
            title=lm.get("title"),
            fields=lm.get("fields") if isinstance(lm.get("fields"), dict) else None,
        )
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=500)
    local = s.transport.node_destination_hash or ""
    return web.json_response({"message": "ok", "lxmf_message": s.transport.messaging.to_lxmf_api_dict(msg, local)})


async def _lxmf_conversation(request: web.Request) -> web.Response:
    s = _state(request)
    peer = request.match_info["destination_hash"]
    local = s.transport.node_destination_hash or ""
    count = _int_query(request.query.get("count"), 100) or 100
    order = request.query.get("order") or "asc"
    after_id = _int_query(request.query.get("after_id"))
    rows = s.transport.database.get_conversation_messages(
        local,
        peer,
        limit=count,
        order=order,
        after_id=after_id,
    )
    return web.json_response(
        {"lxmf_messages": [s.transport.messaging.to_lxmf_api_dict(r, local) for r in rows]},
    )


async def _lxmf_delete_conversation(request: web.Request) -> web.Response:
    s = _state(request)
    local = s.transport.node_destination_hash or ""
    s.transport.database.delete_conversation(local, request.match_info["destination_hash"])
    return web.json_response(post_ok())


async def _telephone_status(request: web.Request) -> web.Response:
    return web.json_response(telephone_status(_state(request).transport))


async def _telephone_call(request: web.Request) -> web.Response:
    try:
        call = _state(request).transport.telephony.initiate_call(request.match_info["identity_hash"])
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=500)
    return web.json_response({"message": "calling", "call": call})


async def _telephone_hangup(request: web.Request) -> web.Response:
    _state(request).transport.telephony.hangup()
    return web.json_response(post_ok())


async def _telephone_ringtone(_: web.Request) -> web.Response:
    return web.json_response(telephone_ringtone_status())


async def _share_status(request: web.Request) -> web.Response:
    return web.json_response(_state(request).transport.share.status())


async def _share_patch(request: web.Request) -> web.Response:
    s = _state(request)
    data = await request.json()
    try:
        if isinstance(data, dict) and data.get("path"):
            s.transport.share.set_shared_folder(str(data["path"]))
        if isinstance(data, dict) and "trusted_identities" in data:
            trusted = data["trusted_identities"]
            if isinstance(trusted, list):
                s.transport.share.set_trusted([str(x) for x in trusted])
        s.config.save_state()
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=400)
    return web.json_response(s.transport.share.status())


async def _share_files(request: web.Request) -> web.Response:
    s = _state(request)
    try:
        files = s.transport.share.list_files(request.query.get("path", ""))
    except Exception as exc:
        return web.json_response({"message": str(exc)}, status=400)
    return web.json_response({"files": files})


async def _csrf(request: web.Request) -> web.Response:
    return web.json_response(csrf_token_response(_state(request).csrf_token))


async def _ok(_: web.Request) -> web.Response:
    return web.json_response(post_ok())


async def _catchall(request: web.Request) -> web.Response:
    payload = api_catchall_payload(request.path, request.method)
    return web.json_response(payload if not isinstance(payload, list) else payload)


async def _websocket(request: web.Request) -> web.WebSocketResponse:
    import asyncio

    s = _state(request)
    hub = s.websocket_hub
    if hub._loop is None:
        hub.set_loop(asyncio.get_running_loop())
    ws = web.WebSocketResponse(max_msg_size=50 * 1024 * 1024)
    await ws.prepare(request)
    hub.add(ws)
    try:
        await ws.send_str(json.dumps(websocket_config_message(s.transport, s.config_overrides)))
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "ping":
                await ws.send_str(json.dumps(websocket_pong()))
            elif data.get("type") == "keyboard_shortcuts.get":
                await ws.send_str(json.dumps(keyboard_shortcuts_response()))
    finally:
        hub.remove(ws)
    return ws


async def _index(request: web.Request) -> web.Response:
    index = _state(request).public_dir / "index.html"
    if not index.is_file():
        return web.Response(text="Frontend missing — run pnpm run build-frontend", status=500)
    return web.FileResponse(index, headers={"Cache-Control": "no-cache, no-store"})


async def _manifest(request: web.Request) -> web.Response:
    path = _state(request).public_dir / "manifest.json"
    if not path.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(path)


async def _service_worker(request: web.Request) -> web.Response:
    path = _state(request).public_dir / "service-worker.js"
    if not path.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(path)