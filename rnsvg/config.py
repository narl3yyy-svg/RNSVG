"""Application configuration and Reticulum config bootstrap."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_DEFAULT_RNS_CONFIG = """\
[reticulum]
  enable_transport = False
  discover_interfaces = False
  share_instance = No
  panic_on_interface_error = No

[interfaces]
  [[LAN Auto Discovery]]
    type = AutoInterface
    enabled = no
"""


@dataclass
class AppState:
    current_identity_hash: str | None = None
    display_name: str = "RNSVG User"
    tutorial_seen: bool = False
    changelog_seen_version: str = "0.0.0"
    last_announced_at: int | None = None
    auto_announce_enabled: bool = False
    auto_announce_interval_seconds: int = 300
    telephone_enabled: bool = True
    shared_folder_path: str | None = None
    shared_folder_trusted: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppState:
        trusted = data.get("shared_folder_trusted") or []
        return cls(
            current_identity_hash=data.get("current_identity_hash"),
            display_name=data.get("display_name", "RNSVG User"),
            tutorial_seen=bool(data.get("tutorial_seen", False)),
            changelog_seen_version=str(data.get("changelog_seen_version", "0.0.0")),
            last_announced_at=data.get("last_announced_at"),
            auto_announce_enabled=bool(data.get("auto_announce_enabled", False)),
            auto_announce_interval_seconds=int(data.get("auto_announce_interval_seconds", 300)),
            telephone_enabled=bool(data.get("telephone_enabled", True)),
            shared_folder_path=data.get("shared_folder_path"),
            shared_folder_trusted=list(trusted) if isinstance(trusted, list) else [],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_identity_hash": self.current_identity_hash,
            "display_name": self.display_name,
            "tutorial_seen": self.tutorial_seen,
            "changelog_seen_version": self.changelog_seen_version,
            "last_announced_at": self.last_announced_at,
            "auto_announce_enabled": self.auto_announce_enabled,
            "auto_announce_interval_seconds": self.auto_announce_interval_seconds,
            "telephone_enabled": self.telephone_enabled,
            "shared_folder_path": self.shared_folder_path,
            "shared_folder_trusted": self.shared_folder_trusted,
        }


@dataclass
class AppConfig:
    data_dir: Path = field(default_factory=lambda: Path.home() / ".rnsvg")
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    headless: bool = False
    state: AppState = field(default_factory=AppState)

    @property
    def rns_config_path(self) -> Path:
        return self.data_dir / ".reticulum" / "config"

    @property
    def identity_path(self) -> Path:
        return self.data_dir / "identity"

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "messages.db"

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> AppState:
        self.ensure_data_dir()
        if not self.state_path.is_file():
            self.state = AppState()
            self.save_state()
            return self.state
        try:
            self.state = AppState.from_dict(json.loads(self.state_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            self.state = AppState()
            self.save_state()
        return self.state

    def save_state(self) -> None:
        self.ensure_data_dir()
        self.state_path.write_text(json.dumps(self.state.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def from_env(cls, **overrides: object) -> AppConfig:
        data_dir = Path(os.environ.get("RNSVG_DATA_DIR", str(Path.home() / ".rnsvg")))
        cfg = cls(
            data_dir=data_dir,
            web_host=os.environ.get("RNSVG_HOST", "127.0.0.1"),
            web_port=int(os.environ.get("RNSVG_PORT", "8000")),
        )
        for key, value in overrides.items():
            if hasattr(cfg, key) and value is not None:
                setattr(cfg, key, value)
        cfg.load_state()
        return cfg


def _strip_local_interface_sections(text: str) -> str:
    """Remove invalid LocalInterface blocks (not a real RNS config type)."""
    lines = text.splitlines()
    out: list[str] = []
    section: list[str] = []
    drop_section = False

    def flush() -> None:
        nonlocal section, drop_section
        if section and not drop_section:
            out.extend(section)
        section = []
        drop_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[[") and stripped.endswith("]]"):
            flush()
            section = [line]
            continue
        if section:
            section.append(line)
            if stripped == "type = LocalInterface":
                drop_section = True
            continue
        out.append(line)
    flush()
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def _disable_enabled_auto_interfaces(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    out: list[str] = []
    in_auto = False
    changed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("type = AutoInterface"):
            in_auto = True
        elif stripped.startswith("type ="):
            in_auto = False
        if in_auto and stripped == "enabled = yes":
            out.append(line.replace("enabled = yes", "enabled = no"))
            changed = True
            continue
        out.append(line)
    result = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    return result, changed


def _migrate_legacy_auto_only_config(text: str) -> str | None:
    """Remove invalid LocalInterface blocks and disable conflicting AutoInterface."""
    original = text
    stripped = _strip_local_interface_sections(text)
    changed = stripped != original
    text = stripped

    if "[[Default Interface]]" in original and "[[LAN Auto Discovery]]" not in original:
        return _DEFAULT_RNS_CONFIG

    if "type = AutoInterface" in text:
        text, auto_changed = _disable_enabled_auto_interfaces(text)
        changed = changed or auto_changed

    return text if changed else None


def ensure_rns_config(config_path: Path) -> Path:
    from rnsvg.interfaces_manager import sanitize_rns_config_text

    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.is_file():
        try:
            text = config_path.read_text(encoding="utf-8")
            if "[reticulum]" in text and "[interfaces]" in text:
                sanitized, none_removed = sanitize_rns_config_text(text)
                migrated = _migrate_legacy_auto_only_config(sanitized)
                final = migrated if migrated else sanitized
                if final != text:
                    config_path.write_text(final, encoding="utf-8")
                    if none_removed:
                        print(
                            "RNSVG: cleaned Reticulum config — removed invalid 'None' "
                            "interface values that prevent startup.",
                        )
                    if migrated and migrated != sanitized:
                        print(
                            "RNSVG: adjusted Reticulum config — removed invalid LocalInterface "
                            "and disabled AutoInterface (avoids port conflicts). "
                            "Enable LAN Auto Discovery in Interfaces when no other Reticulum is running.",
                        )
                return config_path
        except OSError:
            pass
    config_path.write_text(_DEFAULT_RNS_CONFIG, encoding="utf-8")
    return config_path