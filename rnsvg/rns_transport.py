"""Reticulum transport with identity, discovery, messaging, telephony, and share."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from rnsvg.config import AppConfig, ensure_rns_config
from rnsvg.database import MessageDatabase
from rnsvg.discovery import ASPECT_NODE, PeerDiscovery, build_app_data
from rnsvg.identity_manager import IdentityManager
from rnsvg.interfaces_manager import InterfacesManager
from rnsvg.messaging import MessageManager
from rnsvg.share import ShareManager
from rnsvg.telephony import TelephonyManager

if TYPE_CHECKING:
    import RNS

APP_NAME = "rnsvg"


class RNSTransport:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self.reticulum: RNS.Reticulum | None = None
        self.identity: RNS.Identity | None = None
        self.node_destination: RNS.Destination | None = None
        self.inbox_destination: RNS.Destination | None = None
        self.telephony_destination: RNS.Destination | None = None
        self.share_destination: RNS.Destination | None = None
        self.identity_manager = IdentityManager(config.data_dir)
        self.discovery = PeerDiscovery()
        self.interfaces = InterfacesManager(config.rns_config_path)
        self.database = MessageDatabase(config.database_path)
        self.messaging = MessageManager(database=self.database, discovery=self.discovery)
        self.telephony = TelephonyManager()
        self.share = ShareManager(config.data_dir, config.state)

    @property
    def config_dir(self) -> Path:
        return self._config.rns_config_path.parent

    @property
    def display_name(self) -> str:
        return self._config.state.display_name

    @property
    def current_identity_hash(self) -> str | None:
        return self._config.state.current_identity_hash

    @property
    def node_destination_hash(self) -> str | None:
        return self.node_destination.hash.hex() if self.node_destination else None

    def start(self) -> None:
        import RNS

        self._config.ensure_data_dir()
        ensure_rns_config(self._config.rns_config_path)
        self.reticulum = RNS.Reticulum(configdir=str(self.config_dir))
        self._bootstrap_identity()
        self.discovery.register_handlers()
        self._register_destinations()
        self.telephony.enabled = self._config.state.telephone_enabled
        self._record_local_announce()

    def _bootstrap_identity(self) -> None:
        self.identity_manager.ensure_layout()
        self.identity_manager.migrate_legacy_identity()
        identities = self.identity_manager.list_identities()
        if not identities:
            created = self.identity_manager.create_identity(self.display_name)
            self._config.state.current_identity_hash = created["hash"]
            self._config.save_state()
            identities = self.identity_manager.list_identities(created["hash"])

        current = self._config.state.current_identity_hash
        if not current or not any(i["hash"] == current for i in identities):
            current = identities[0]["hash"]
            self._config.state.current_identity_hash = current
            self._config.save_state()

        self.identity = self.identity_manager.load_identity(current)
        self.identity_manager.set_active_identity_file(current)
        name = self.identity_manager.get_display_name(current)
        if name and name != "Anonymous Peer":
            self._config.state.display_name = name

    def _register_destinations(self) -> None:
        import RNS

        if self.identity is None:
            return
        self._deregister_destinations()

        self.node_destination = RNS.Destination(
            self.identity, RNS.Destination.IN, RNS.Destination.SINGLE, APP_NAME, "node",
        )
        self.inbox_destination = RNS.Destination(
            self.identity, RNS.Destination.IN, RNS.Destination.SINGLE, APP_NAME, "inbox",
        )
        self.telephony_destination = RNS.Destination(
            self.identity, RNS.Destination.IN, RNS.Destination.SINGLE, APP_NAME, "telephony",
        )
        self.share_destination = RNS.Destination(
            self.identity, RNS.Destination.IN, RNS.Destination.SINGLE, APP_NAME, "share",
        )

        node_hash = self.node_destination.hash.hex()
        telephony_hash = self.telephony_destination.hash.hex()
        if self.current_identity_hash:
            self.identity_manager.update_metadata(
                self.current_identity_hash,
                node_address=node_hash,
                telephony_address=telephony_hash,
                display_name=self.display_name,
            )

        self.messaging.attach(self.identity, self.inbox_destination, node_hash)
        self.telephony.attach(self.identity, self.telephony_destination)

    def _deregister_destinations(self) -> None:
        import RNS

        for dest in (
            self.node_destination,
            self.inbox_destination,
            self.telephony_destination,
            self.share_destination,
        ):
            if dest is not None:
                try:
                    RNS.Transport.deregister_destination(dest)
                except Exception:
                    pass
        self.node_destination = None
        self.inbox_destination = None
        self.telephony_destination = None
        self.share_destination = None

    def switch_identity(self, identity_hash: str) -> None:
        self.identity_manager.ensure_identity_exists(identity_hash)
        self.identity = self.identity_manager.load_identity(identity_hash)
        self.identity_manager.set_active_identity_file(identity_hash)
        self._config.state.current_identity_hash = identity_hash
        self._config.state.display_name = self.identity_manager.get_display_name(
            identity_hash, self._config.state.display_name,
        )
        self._config.save_state()
        self._register_destinations()
        self._record_local_announce()

    def set_display_name(self, display_name: str) -> None:
        self._config.state.display_name = display_name
        self._config.save_state()
        if self.current_identity_hash:
            self.identity_manager.update_metadata(
                self.current_identity_hash, display_name=display_name,
            )

    def announce(self) -> None:
        if not self.node_destination or not self.identity:
            raise RuntimeError("Destination not ready")
        app_data = build_app_data(self.display_name)
        self.node_destination.display_name = self.display_name
        self.node_destination.announce(app_data)
        self._config.state.last_announced_at = int(time.time())
        self._config.save_state()
        self.discovery.record_local_announce(
            aspect=ASPECT_NODE,
            destination_hash=self.node_destination.hash.hex(),
            identity=self.identity,
            display_name=self.display_name,
            app_data=app_data,
        )

    def _record_local_announce(self) -> None:
        if not self.node_destination or not self.identity:
            return
        self.discovery.record_local_announce(
            aspect=ASPECT_NODE,
            destination_hash=self.node_destination.hash.hex(),
            identity=self.identity,
            display_name=self.display_name,
            app_data=build_app_data(self.display_name),
        )

    def create_identity(self, display_name: str | None = None) -> dict:
        return self.identity_manager.create_identity(display_name or self.display_name)

    def delete_identity(self, identity_hash: str) -> bool:
        if identity_hash == self.current_identity_hash:
            raise ValueError("Cannot delete the active identity")
        return self.identity_manager.delete_identity(identity_hash)

    def restore_identity_from_bytes(self, identity_bytes: bytes, display_name: str | None = None) -> dict:
        return self.identity_manager.restore_from_bytes(identity_bytes, display_name)

    def restore_identity_from_base32(self, base32_value: str, display_name: str | None = None) -> dict:
        return self.identity_manager.restore_from_base32(base32_value, display_name)

    def reload_reticulum(self) -> None:
        if self.reticulum is not None:
            try:
                self.reticulum.reload_interfaces()
            except Exception:
                pass

    def is_running(self) -> bool:
        return self.reticulum is not None

    def transport_enabled(self) -> bool:
        if self.reticulum is None:
            return False
        try:
            return bool(self.reticulum.transport_enabled())
        except Exception:
            return False