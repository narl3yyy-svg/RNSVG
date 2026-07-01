"""Shared folder access for trusted peers over RNS."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ShareManager:
    def __init__(self, data_dir: Path, state: Any) -> None:
        self.data_dir = Path(data_dir)
        self.state = state

    @property
    def shared_path(self) -> Path | None:
        raw = getattr(self.state, "shared_folder_path", None)
        if not raw:
            return None
        path = Path(raw).expanduser()
        return path if path.is_dir() else None

    @property
    def trusted_identities(self) -> list[str]:
        return list(getattr(self.state, "shared_folder_trusted", []) or [])

    def set_shared_folder(self, path: str) -> dict[str, Any]:
        expanded = Path(path).expanduser().resolve()
        if not expanded.is_dir():
            raise ValueError("Path must be an existing directory")
        self.state.shared_folder_path = str(expanded)
        return self.status()

    def set_trusted(self, identity_hashes: list[str]) -> dict[str, Any]:
        self.state.shared_folder_trusted = [h.strip().lower() for h in identity_hashes if h.strip()]
        return self.status()

    def is_trusted(self, identity_hash: str) -> bool:
        trusted = {h.lower() for h in self.trusted_identities}
        return identity_hash.lower() in trusted if trusted else False

    def list_files(self, subpath: str = "") -> list[dict[str, Any]]:
        root = self.shared_path
        if root is None:
            return []
        target = (root / subpath).resolve()
        if not str(target).startswith(str(root.resolve())):
            raise ValueError("Invalid path")
        if not target.exists():
            return []
        entries: list[dict[str, Any]] = []
        for name in sorted(os.listdir(target)):
            full = target / name
            entries.append(
                {
                    "name": name,
                    "path": str(full.relative_to(root)),
                    "is_dir": full.is_dir(),
                    "size": full.stat().st_size if full.is_file() else None,
                },
            )
        return entries

    def status(self) -> dict[str, Any]:
        root = self.shared_path
        return {
            "enabled": root is not None,
            "path": str(root) if root else None,
            "trusted_identities": self.trusted_identities,
            "file_count": len(self.list_files()) if root else 0,
        }

    def manifest_bytes(self) -> bytes:
        return json.dumps(self.status(), indent=2).encode("utf-8")