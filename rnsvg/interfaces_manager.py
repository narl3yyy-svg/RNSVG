"""Read and write Reticulum interface definitions in the config file."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import RNS.vendor.configobj

_NONE_CONFIG_LINE = re.compile(r"^\s+\S+\s*=\s*None\s*$", re.IGNORECASE)


INTERFACE_HELP: dict[str, str] = {
    "TCPClientInterface": (
        "Connect outbound to a remote Reticulum peer over TCP. Use this when you know "
        "the host and port of a community node or friend’s backbone (for example "
        "example.com:4242)."
    ),
    "TCPServerInterface": (
        "Listen for inbound TCP connections from other Reticulum nodes. Run this when "
        "you want others to connect to your machine as a backbone or hub."
    ),
    "UDPInterface": (
        "Low-latency UDP transport, usually on a LAN or trusted network. Both sides must "
        "use matching IP, port, and optional password settings."
    ),
    "BackboneInterface": (
        "Public relay/backbone mode for helping route traffic across the wider mesh. "
        "Only enable if you intend to carry transit for others and have bandwidth for it."
    ),
    "RNodeInterface": (
        "Radio link through an RNode (LoRa). Requires a compatible RNode firmware and "
        "serial/USB connection with correct frequency and bandwidth settings."
    ),
    "RNodeMultiInterface": (
        "Multiple RNode sub-interfaces in one group — useful when you run more than one "
        "radio on the same host."
    ),
    "I2PInterface": (
        "Tunnel Reticulum over I2P for censorship-resistant connectivity. Slower than "
        "direct TCP but useful when plain internet paths are blocked."
    ),
    "TunnelInterface": (
        "Generic tunnel interface for wrapping Reticulum inside another transport "
        "provided by an external tool or script."
    ),
    "SerialInterface": (
        "Raw serial port link to hardware (radio modem, MCU, etc.). Set the correct "
        "device path and baud rate for your adapter."
    ),
    "KISSInterface": (
        "Amateur-radio TNC using the KISS protocol over serial. Common for packet radio "
        "gateways and APRS-style setups."
    ),
    "AutoInterface": (
        "Automatic discovery on your local network (multicast). Easiest way to find nearby "
        "peers on the same LAN without manual addressing."
    ),
    "LocalInterface": (
        "Loopback-only interface for testing on this machine. Does not reach other "
        "computers — useful for development and single-host experiments."
    ),
}


class InterfacesManager:
    def __init__(self, config_path: Path) -> None:
        self.config_path = Path(config_path)

    def read_config_text(self) -> str:
        if not self.config_path.is_file():
            return "[reticulum]\n  enable_transport = False\n\n[interfaces]\n"
        return self.config_path.read_text(encoding="utf-8")

    def write_config_text(self, text: str) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(text, encoding="utf-8")

    def list_interfaces(self) -> dict[str, dict[str, Any]]:
        config = self._load_configobj()
        interfaces = config.get("interfaces", {}) or {}
        out: dict[str, dict[str, Any]] = {}
        for name, data in interfaces.items():
            if not isinstance(data, dict):
                continue
            entry = copy.deepcopy(data)
            entry["name"] = name
            entry["type"] = entry.get("type", "Unknown")
            entry["interface_enabled"] = str(entry.get("enabled", "no")).lower() in {
                "yes",
                "true",
                "1",
                "on",
            }
            entry["help"] = INTERFACE_HELP.get(entry["type"], "")
            out[name] = entry
        return out

    def add_interface(self, name: str, interface_type: str, fields: dict[str, Any]) -> None:
        config = self._load_configobj()
        if "interfaces" not in config:
            config["interfaces"] = {}
        iface = {"type": interface_type, "enabled": _normalize_enabled(fields.get("enabled", "yes"))}
        for key, value in fields.items():
            if key in {"name", "type", "enabled"}:
                continue
            normalized = _normalize_config_value(value)
            if normalized is not None:
                iface[key] = normalized
        config["interfaces"][name] = iface
        self._save_configobj(config)

    def set_interface_enabled(self, name: str, enabled: bool) -> bool:
        config = self._load_configobj()
        interfaces = config.get("interfaces", {}) or {}
        if name not in interfaces:
            return False
        interfaces[name]["enabled"] = "yes" if enabled else "no"
        self._save_configobj(config)
        return True

    def delete_interface(self, name: str) -> bool:
        config = self._load_configobj()
        interfaces = config.get("interfaces", {}) or {}
        if name not in interfaces:
            return False
        del interfaces[name]
        self._save_configobj(config)
        return True

    def get_help(self, interface_type: str) -> str:
        return INTERFACE_HELP.get(interface_type, "")

    def _load_configobj(self) -> RNS.vendor.configobj.ConfigObj:
        text = self.read_config_text()
        lines = text.splitlines()
        if "[interfaces]" not in [ln.strip() for ln in lines]:
            lines.append("[interfaces]")
        return RNS.vendor.configobj.ConfigObj(lines)

    def _save_configobj(self, config: RNS.vendor.configobj.ConfigObj) -> None:
        text = "\n".join(config.write())
        sanitized, _ = sanitize_rns_config_text(text)
        self.write_config_text(sanitized)


def _normalize_enabled(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return "yes"
    text = str(value).strip().lower()
    if text in {"yes", "true", "1", "on"}:
        return "yes"
    return "no"


def _normalize_config_value(value: Any) -> Any | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() == "none":
            return None
        return stripped
    if isinstance(value, bool):
        return "yes" if value else "no"
    return value


def sanitize_rns_config_text(text: str) -> tuple[str, bool]:
    """Drop ``key = None`` lines — Reticulum cannot parse them as integers."""
    lines = text.splitlines()
    out: list[str] = []
    changed = False
    for line in lines:
        if _NONE_CONFIG_LINE.match(line):
            changed = True
            continue
        out.append(line)
    result = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    return result, changed