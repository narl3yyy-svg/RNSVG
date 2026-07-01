"""Text messaging over raw RNS packets to rnsvg.inbox."""

from __future__ import annotations

import json
import threading
import time
from typing import TYPE_CHECKING, Any, Callable

from rnsvg.database import MessageDatabase

if TYPE_CHECKING:
    import RNS

    from rnsvg.discovery import PeerDiscovery

APP_NAME = "rnsvg"
ASPECT_INBOX = "inbox"
ASPECT_NODE = "node"


class MessageManager:
    def __init__(
        self,
        *,
        database: MessageDatabase,
        discovery: PeerDiscovery | None = None,
        on_message: Callable[[dict[str, Any], str], None] | None = None,
        on_outbound: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.database = database
        self.discovery = discovery
        self._on_message = on_message
        self._on_outbound = on_outbound
        self._lock = threading.Lock()
        self.inbox_destination: RNS.Destination | None = None
        self._identity_hash: str | None = None
        self._node_hash: str | None = None

    def attach(
        self,
        identity: RNS.Identity,
        inbox_destination: RNS.Destination,
        node_hash: str,
    ) -> None:
        self.inbox_destination = inbox_destination
        self._identity_hash = identity.hash.hex()
        self._node_hash = node_hash
        inbox_destination.set_packet_callback(self._on_packet)

    def send_text(
        self,
        *,
        destination_hash: str,
        content: str,
        title: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        import RNS

        if self._identity_hash is None or self._node_hash is None:
            raise RuntimeError("Messaging is not initialized")

        peer_node_hash = destination_hash.lower()
        payload = json.dumps(
            {
                "type": "text",
                "content": content,
                "title": title,
                "fields": fields or {},
                "source_node_hash": self._node_hash,
            },
        ).encode("utf-8")

        state = "outbound"
        try:
            out_dest = self._peer_inbox_destination(peer_node_hash)
            packet = RNS.Packet(out_dest, payload)
            packet.send()
            state = "sent"
        except Exception:
            state = "failed"

        msg = self.database.insert_message(
            source_hash=self._node_hash,
            destination_hash=peer_node_hash,
            direction="outbound",
            content=content,
            title=title,
            fields=fields,
            state=state,
        )
        if self._on_outbound:
            self._on_outbound(msg)
        return msg

    def handle_incoming_packet(self, data: bytes, packet: Any) -> None:
        if self._identity_hash is None or self._node_hash is None:
            return
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if payload.get("type") != "text":
            return

        source_hash = self._resolve_source_node_hash(payload, packet)
        if not source_hash:
            return

        msg = self.database.insert_message(
            source_hash=source_hash,
            destination_hash=self._node_hash,
            direction="inbound",
            content=str(payload.get("content", "")),
            title=payload.get("title"),
            fields=payload.get("fields"),
            state="delivered",
        )
        if self._on_message:
            self._on_message(msg, source_hash)

    def _resolve_source_node_hash(self, payload: dict[str, Any], packet: Any) -> str | None:
        import RNS

        explicit = payload.get("source_node_hash")
        if isinstance(explicit, str) and len(explicit) == 32:
            return explicit.lower()

        transport_id = getattr(packet, "transport_id", None)
        if transport_id and len(transport_id) == RNS.Reticulum.TRUNCATED_HASHLENGTH // 8:
            return RNS.Destination.hash(transport_id, APP_NAME, ASPECT_NODE).hex()

        destination_hash = getattr(packet, "destination_hash", None)
        if destination_hash:
            return destination_hash.hex()

        return None

    def _peer_inbox_destination(self, peer_node_hash: str) -> RNS.Destination:
        import RNS

        identity = RNS.Identity.recall(bytes.fromhex(peer_node_hash))
        if identity is None and self.discovery is not None:
            records, _ = self.discovery.list_announces(destination_hash=peer_node_hash)
            if records:
                identity = RNS.Identity.recall(
                    bytes.fromhex(records[0].identity_hash),
                    from_identity_hash=True,
                )
        if identity is None:
            raise RuntimeError(f"Unknown peer destination: {peer_node_hash}")
        return RNS.Destination(
            identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            APP_NAME,
            ASPECT_INBOX,
        )

    def _on_packet(self, data: bytes, packet: Any) -> None:
        self.handle_incoming_packet(data, packet)

    def to_lxmf_api_dict(self, row: dict[str, Any], local_hash: str) -> dict[str, Any]:
        fields_raw = row.get("fields") or "{}"
        try:
            fields = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw
        except json.JSONDecodeError:
            fields = {}
        outbound = row.get("source_hash") == local_hash
        return {
            "id": row.get("id"),
            "hash": row["hash"],
            "source_hash": row["source_hash"],
            "destination_hash": row["destination_hash"],
            "title": row.get("title"),
            "content": row.get("content"),
            "fields": fields,
            "state": row.get("state", "delivered"),
            "timestamp": row.get("timestamp", time.time()),
            "created_at": row.get("created_at"),
            "is_outbound": outbound,
            "is_incoming": not outbound,
            "delivery_attempts": 0,
            "progress": 100.0 if row.get("state") in {"sent", "delivered"} else 0.0,
            "method": "direct",
        }

    def delivery_event(self, row: dict[str, Any], local_hash: str, remote_name: str) -> dict[str, Any]:
        return {
            "type": "lxmf.delivery",
            "remote_identity_name": remote_name,
            "lxmf_message": self.to_lxmf_api_dict(row, local_hash),
        }

    def created_event(self, row: dict[str, Any], local_hash: str) -> dict[str, Any]:
        return {
            "type": "lxmf_message_created",
            "lxmf_message": self.to_lxmf_api_dict(row, local_hash),
        }