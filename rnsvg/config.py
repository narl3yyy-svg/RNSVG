"""Application configuration and Reticulum config bootstrap."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


_DEFAULT_RNS_CONFIG = """\
[reticulum]
  enable_transport = False
  discover_interfaces = False
  share_instance = No
  panic_on_interface_error = No

[interfaces]
  [[Default Interface]]
    type = AutoInterface
    enabled = yes
"""


@dataclass
class AppConfig:
    """Runtime configuration for the RNSVG stub server."""

    data_dir: Path = field(default_factory=lambda: Path.home() / ".rnsvg")
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    headless: bool = False

    @property
    def rns_config_path(self) -> Path:
        return self.data_dir / ".reticulum" / "config"

    @property
    def identity_path(self) -> Path:
        return self.data_dir / "identity"

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, **overrides: object) -> AppConfig:
        data_dir = Path(
            os.environ.get("RNSVG_DATA_DIR", str(Path.home() / ".rnsvg")),
        )
        web_host = os.environ.get("RNSVG_HOST", "127.0.0.1")
        web_port = int(os.environ.get("RNSVG_PORT", "8000"))
        cfg = cls(data_dir=data_dir, web_host=web_host, web_port=web_port)
        for key, value in overrides.items():
            if hasattr(cfg, key) and value is not None:
                setattr(cfg, key, value)
        return cfg


def ensure_rns_config(config_path: Path) -> Path:
    """Write a minimal Reticulum config if missing or invalid."""
    config_path = Path(config_path)
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)

    needs_write = True
    if config_path.is_file():
        try:
            content = config_path.read_text(encoding="utf-8")
            if "[reticulum]" in content and "[interfaces]" in content:
                needs_write = False
        except OSError:
            pass

    if needs_write:
        config_path.write_text(_DEFAULT_RNS_CONFIG, encoding="utf-8")

    return config_path