"""Voice calls over raw RNS Links and Buffers (no LXST)."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import RNS


class TelephonyManager:
    """Minimal RNS-native telephony signaling scaffold."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.telephony_destination: RNS.Destination | None = None
        self.enabled = True
        self.active_call: dict[str, Any] | None = None
        self._identity_hash: str | None = None

    def attach(self, identity: RNS.Identity, destination: RNS.Destination) -> None:
        self.telephony_destination = destination
        self._identity_hash = identity.hash.hex()
        destination.set_link_established_callback(self._on_link_established)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "message": "RNS Voice (raw Reticulum — no LXST)",
            "active_call": self.active_call,
            "transport": "rns.buffer",
        }

    def initiate_call(self, remote_identity_hash: str) -> dict[str, Any]:
        import RNS

        if self.telephony_destination is None:
            raise RuntimeError("Telephony is not initialized")
        remote_dest = RNS.Destination(
            bytes.fromhex(remote_identity_hash),
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
        )
        link = RNS.Link(remote_dest)
        with self._lock:
            self.active_call = {
                "hash": link.link_id.hex() if hasattr(link, "link_id") else "pending",
                "remote_identity_hash": remote_identity_hash,
                "state": "ringing",
                "direction": "outbound",
            }
        return self.active_call

    def hangup(self) -> None:
        with self._lock:
            self.active_call = None

    def _on_link_established(self, link: Any) -> None:
        with self._lock:
            if self.active_call:
                self.active_call["state"] = "active"

