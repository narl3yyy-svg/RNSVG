"""Peer discovery via Reticulum announces."""

from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import RNS

ASPECT_NODE = "rnsvg.node"
ASPECT_API_ALIASES = {"lxmf.delivery": ASPECT_NODE, "rnsvg.node": ASPECT_NODE}


@dataclass
class AnnounceRecord:
    id: int
    destination_hash: str
    aspect: str
    identity_hash: str
    identity_public_key: str
    app_data: str | None
    display_name: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_local: bool = False


class AnnounceHandler:
    def __init__(self, aspect_filter: str, store: PeerDiscovery) -> None:
        self.aspect_filter = aspect_filter
        self._store = store

    def received_announce(
        self,
        destination_hash: bytes | str,
        announced_identity: RNS.Identity,
        app_data: bytes | None,
        announce_packet_hash: bytes | None = None,
    ) -> None:
        del announce_packet_hash
        dest = destination_hash.hex() if isinstance(destination_hash, bytes) else destination_hash
        self._store.record_remote_announce(
            aspect=self.aspect_filter,
            destination_hash=dest,
            identity=announced_identity,
            app_data=app_data,
        )


class PeerDiscovery:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[tuple[str, str], AnnounceRecord] = {}
        self._next_id = 1

    def register_handlers(self) -> None:
        import RNS

        for aspect in (ASPECT_NODE, "lxmf.delivery"):
            RNS.Transport.register_announce_handler(AnnounceHandler(aspect, self))

    def record_remote_announce(
        self,
        *,
        aspect: str,
        destination_hash: str,
        identity: RNS.Identity,
        app_data: bytes | None,
    ) -> AnnounceRecord:
        return self._upsert(
            aspect=aspect,
            destination_hash=destination_hash,
            identity_hash=identity.hash.hex(),
            identity_public_key=base64.b64encode(identity.get_public_key()).decode("ascii"),
            app_data=app_data,
            display_name=_parse_display_name(app_data),
            is_local=False,
        )

    def record_local_announce(
        self,
        *,
        aspect: str,
        destination_hash: str,
        identity: RNS.Identity,
        display_name: str,
        app_data: bytes | None = None,
    ) -> AnnounceRecord:
        return self._upsert(
            aspect=aspect,
            destination_hash=destination_hash,
            identity_hash=identity.hash.hex(),
            identity_public_key=base64.b64encode(identity.get_public_key()).decode("ascii"),
            app_data=app_data or display_name.encode("utf-8"),
            display_name=display_name,
            is_local=True,
        )

    def _upsert(
        self,
        *,
        aspect: str,
        destination_hash: str,
        identity_hash: str,
        identity_public_key: str,
        app_data: bytes | None,
        display_name: str,
        is_local: bool,
    ) -> AnnounceRecord:
        app_b64 = base64.b64encode(app_data).decode("ascii") if app_data else None
        now = time.time()
        key = (destination_hash, aspect)
        with self._lock:
            existing = self._records.get(key)
            if existing:
                existing.identity_hash = identity_hash
                existing.identity_public_key = identity_public_key
                existing.app_data = app_b64
                existing.display_name = display_name or existing.display_name
                existing.updated_at = now
                existing.is_local = is_local or existing.is_local
                return existing
            record = AnnounceRecord(
                id=self._next_id,
                destination_hash=destination_hash,
                aspect=aspect,
                identity_hash=identity_hash,
                identity_public_key=identity_public_key,
                app_data=app_b64,
                display_name=display_name or "Anonymous Peer",
                created_at=now,
                updated_at=now,
                is_local=is_local,
            )
            self._next_id += 1
            self._records[key] = record
            return record

    def list_announces(
        self,
        *,
        aspect: str | None = None,
        identity_hash: str | None = None,
        destination_hash: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[AnnounceRecord], int]:
        canonical = ASPECT_API_ALIASES.get(aspect, aspect) if aspect else None
        with self._lock:
            records = list(self._records.values())
        if canonical:
            records = [r for r in records if r.aspect == canonical]
        if identity_hash:
            records = [r for r in records if r.identity_hash == identity_hash]
        if destination_hash:
            records = [r for r in records if r.destination_hash == destination_hash]
        records.sort(key=lambda r: r.updated_at, reverse=True)
        total = len(records)
        start = max(offset, 0)
        end = start + limit if limit is not None else total
        return records[start:end], total

    def to_api_dict(
        self,
        record: AnnounceRecord,
        *,
        aspect_override: str | None = None,
    ) -> dict[str, Any]:
        import RNS

        hops = 0
        try:
            hops = RNS.Transport.hops_to(bytes.fromhex(record.destination_hash))
        except Exception:
            pass
        aspect = aspect_override or record.aspect
        return {
            "id": record.id,
            "destination_hash": record.destination_hash,
            "aspect": aspect,
            "identity_hash": record.identity_hash,
            "identity_public_key": record.identity_public_key,
            "app_data": record.app_data,
            "hops": hops,
            "rssi": None,
            "snr": None,
            "quality": None,
            "display_name": record.display_name,
            "lxmf_destination_hash": record.destination_hash if aspect == "lxmf.delivery" else None,
            "custom_display_name": None,
            "lxmf_user_icon": None,
            "created_at": _iso_z(record.created_at),
            "updated_at": _iso_z(record.updated_at),
            "is_local": record.is_local,
        }


def build_app_data(display_name: str) -> bytes:
    return display_name.encode("utf-8")


def _parse_display_name(app_data: bytes | None, default: str = "Anonymous Peer") -> str:
    if not app_data:
        return default
    try:
        text = app_data.decode("utf-8").strip()
        return text or default
    except UnicodeDecodeError:
        return default


def _iso_z(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))