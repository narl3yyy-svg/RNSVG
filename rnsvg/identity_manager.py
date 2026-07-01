"""Persistent RNS identity storage under ~/.rnsvg/identities/."""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import RNS


class IdentityManager:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.identities_dir = self.data_dir / "identities"
        self.legacy_identity_path = self.data_dir / "identity"

    def ensure_layout(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.identities_dir.mkdir(parents=True, exist_ok=True)

    def migrate_legacy_identity(self) -> str | None:
        if not self.legacy_identity_path.is_file():
            return None
        import RNS

        try:
            identity = RNS.Identity.from_file(str(self.legacy_identity_path))
        except Exception:
            return None
        identity_hash = identity.hash.hex()
        identity_dir = self.identities_dir / identity_hash
        if identity_dir.is_dir():
            return identity_hash
        identity_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.legacy_identity_path, identity_dir / "identity")
        self._write_metadata(identity_hash, {"display_name": "RNSVG User"})
        return identity_hash

    def list_identities(self, current_identity_hash: str | None = None) -> list[dict[str, Any]]:
        self.ensure_layout()
        identities: list[dict[str, Any]] = []
        for entry in sorted(self.identities_dir.iterdir()):
            if not entry.is_dir() or not (entry / "identity").is_file():
                continue
            hash_str = entry.name
            meta = self._read_metadata(hash_str)
            identities.append(
                {
                    "hash": hash_str,
                    "display_name": meta.get("display_name", "Anonymous Peer"),
                    "icon_name": meta.get("icon_name"),
                    "icon_foreground_colour": meta.get("icon_foreground_colour"),
                    "icon_background_colour": meta.get("icon_background_colour"),
                    "node_address": meta.get("node_address"),
                    "telephony_address": meta.get("telephony_address"),
                    "is_current": hash_str == current_identity_hash,
                    "message_count": meta.get("message_count", 0),
                },
            )
        return identities

    def create_identity(self, display_name: str | None = None) -> dict[str, Any]:
        import RNS

        return self._save_new_identity(RNS.Identity(create_keys=True), display_name or "Anonymous Peer")

    def restore_from_bytes(self, identity_bytes: bytes, display_name: str | None = None) -> dict[str, Any]:
        import RNS

        identity = RNS.Identity(create_keys=False)
        if not identity.load_private_key(identity_bytes):
            raise ValueError("Invalid identity key data")
        return self._save_new_identity(identity, display_name or "Anonymous Peer", allow_existing=True)

    def restore_from_base32(self, base32_value: str, display_name: str | None = None) -> dict[str, Any]:
        cleaned = "".join(base32_value.split()).upper()
        return self.restore_from_bytes(base64.b32decode(cleaned, casefold=True), display_name)

    def load_identity(self, identity_hash: str) -> RNS.Identity:
        import RNS

        path = self.identities_dir / identity_hash / "identity"
        if not path.is_file():
            raise FileNotFoundError(identity_hash)
        return RNS.Identity.from_file(str(path))

    def ensure_identity_exists(self, identity_hash: str) -> None:
        if not (self.identities_dir / identity_hash / "identity").is_file():
            raise FileNotFoundError(identity_hash)

    def delete_identity(self, identity_hash: str) -> bool:
        path = self.identities_dir / identity_hash
        if not path.is_dir():
            return False
        shutil.rmtree(path)
        return True

    def set_active_identity_file(self, identity_hash: str) -> None:
        source = self.identities_dir / identity_hash / "identity"
        shutil.copy2(source, self.legacy_identity_path)

    def update_metadata(self, identity_hash: str, **fields: Any) -> dict[str, Any]:
        meta = self._read_metadata(identity_hash)
        meta.update({k: v for k, v in fields.items() if v is not None})
        self._write_metadata(identity_hash, meta)
        return meta

    def get_display_name(self, identity_hash: str, fallback: str = "Anonymous Peer") -> str:
        return self._read_metadata(identity_hash).get("display_name") or fallback

    def get_identity_backup_bytes(self, identity_hash: str) -> bytes:
        return (self.identities_dir / identity_hash / "identity").read_bytes()

    def get_identity_base32(self, identity_hash: str) -> str:
        return base64.b32encode(self.get_identity_backup_bytes(identity_hash)).decode("utf-8")

    def export_all_bytes(self) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        for item in self.list_identities():
            try:
                out[item["hash"]] = self.get_identity_backup_bytes(item["hash"])
            except OSError:
                pass
        return out

    def _save_new_identity(
        self,
        identity: RNS.Identity,
        display_name: str,
        *,
        allow_existing: bool = False,
    ) -> dict[str, Any]:
        import RNS

        self.ensure_layout()
        identity_hash = identity.hash.hex()
        identity_dir = self.identities_dir / identity_hash
        if identity_dir.exists() and not allow_existing:
            raise ValueError("Identity already exists")
        identity_dir.mkdir(parents=True, exist_ok=True)
        (identity_dir / "identity").write_bytes(identity.get_private_key())
        node_address = RNS.Destination.hash(identity, "rnsvg", "node").hex()
        telephony_address = RNS.Destination.hash(identity, "rnsvg", "telephony").hex()
        self._write_metadata(
            identity_hash,
            {
                "display_name": display_name,
                "node_address": node_address,
                "telephony_address": telephony_address,
            },
        )
        self.set_active_identity_file(identity_hash)
        return {"hash": identity_hash, "display_name": display_name, "node_address": node_address}

    def _read_metadata(self, identity_hash: str) -> dict[str, Any]:
        path = self.identities_dir / identity_hash / "metadata.json"
        if not path.is_file():
            return {"display_name": "Anonymous Peer"}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"display_name": "Anonymous Peer"}

    def _write_metadata(self, identity_hash: str, metadata: dict[str, Any]) -> None:
        path = self.identities_dir / identity_hash / "metadata.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")