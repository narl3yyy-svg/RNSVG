"""Minimal Reticulum transport bootstrap."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rnsvg.config import AppConfig, ensure_rns_config

if TYPE_CHECKING:
    import RNS


class RNSTransport:
    """Initialize Reticulum with an optional on-disk identity."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self.reticulum: RNS.Reticulum | None = None
        self.identity: RNS.Identity | None = None

    @property
    def config_dir(self) -> Path:
        return self._config.rns_config_path.parent

    def start(self) -> None:
        import RNS

        self._config.ensure_data_dir()
        ensure_rns_config(self._config.rns_config_path)
        self.reticulum = RNS.Reticulum(configdir=str(self.config_dir))
        self._load_identity()

    def _load_identity(self) -> None:
        import RNS

        identity_path = self._config.identity_path
        if not identity_path.is_file():
            return
        try:
            self.identity = RNS.Identity.from_file(str(identity_path))
        except Exception as exc:
            print(f"Warning: failed to load identity from {identity_path}: {exc}")

    def is_running(self) -> bool:
        return self.reticulum is not None

    def transport_enabled(self) -> bool:
        if self.reticulum is None:
            return False
        try:
            return bool(self.reticulum.transport_enabled())
        except Exception:
            return False