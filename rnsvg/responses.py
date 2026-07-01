"""JSON response builders matching MeshChatX API shapes."""

from __future__ import annotations

import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from rnsvg.config import AppConfig
from rnsvg.rns_transport import RNSTransport
from rnsvg.version import __version__


def _package_version(name: str, fallback: str = "unknown") -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return fallback


def auth_status() -> dict[str, bool]:
    return {
        "auth_enabled": False,
        "password_set": False,
        "authenticated": False,
    }


def api_status() -> dict[str, str]:
    return {"status": "ok"}


def csrf_token_response(token: str) -> dict[str, str]:
    return {"csrf_token": token}


def blocked_destinations() -> dict[str, list]:
    return {"blocked_destinations": []}


def announce_response() -> dict[str, str]:
    return {"message": "announcing"}


def identities_response(transport: RNSTransport) -> dict[str, list[dict[str, Any]]]:
    identities: list[dict[str, Any]] = []
    identity = transport.identity
    if identity is not None:
        identities.append(
            {
                "identity_hash": identity.hash.hex(),
                "display_name": "RNSVG",
                "is_current": True,
                "message_count": 0,
            },
        )
    return {"identities": identities}


def notifications_response() -> dict[str, Any]:
    return {
        "notifications": [],
        "unread_count": 0,
        "lxmf_total_unread_count": 0,
    }


def lxmf_conversations() -> dict[str, list]:
    return {"conversations": []}


def lxmf_conversation_pins() -> dict[str, list]:
    return {"peer_hashes": []}


def lxmf_folders() -> list:
    return []


def propagation_node_status() -> dict[str, Any]:
    return {
        "propagation_node_status": {
            "state": "idle",
            "progress": 0,
            "messages_received": None,
            "messages_stored": 0,
            "delivery_confirmations": 0,
            "messages_hidden": 0,
        },
        "local_propagation_node": None,
    }


def telephone_status() -> dict[str, Any]:
    return {
        "enabled": False,
        "message": "Telephone is disabled",
        "active_call": None,
    }


def telephone_ringtone_status() -> dict[str, Any]:
    return {
        "has_custom_ringtone": False,
        "enabled": False,
        "filename": None,
        "id": None,
        "volume": 1.0,
    }


def build_config_dict(transport: RNSTransport) -> dict[str, Any]:
    identity = transport.identity
    identity_hash = identity.hash.hex() if identity is not None else ""
    identity_public_key = (
        identity.get_public_key().hex() if identity is not None else ""
    )

    return {
        "display_name": "RNSVG",
        "identity_hash": identity_hash,
        "identity_public_key": identity_public_key,
        "lxmf_address_hash": None,
        "telephone_address_hash": None,
        "is_transport_enabled": transport.transport_enabled(),
        "auto_announce_enabled": False,
        "auto_announce_interval_seconds": 300,
        "last_announced_at": None,
        "theme": "dark",
        "language": "en",
        "auto_resend_failed_messages_when_announce_received": True,
        "allow_auto_resending_failed_messages_with_attachments": False,
        "auto_send_failed_messages_to_propagation_node": False,
        "show_suggested_community_interfaces": True,
        "lxmf_delivery_transfer_limit_in_bytes": 1000000,
        "lxmf_propagation_transfer_limit_in_bytes": 1000000,
        "lxmf_propagation_sync_limit_in_bytes": 1000000,
        "lxmf_local_propagation_node_enabled": False,
        "lxmf_local_propagation_node_address_hash": None,
        "lxmf_preferred_propagation_node_destination_hash": None,
        "lxmf_preferred_propagation_node_auto_select": False,
        "lxmf_preferred_propagation_node_auto_sync_interval_seconds": 3600,
        "lxmf_preferred_propagation_node_last_synced_at": None,
        "lxmf_user_icon_name": None,
        "lxmf_user_icon_foreground_colour": None,
        "lxmf_user_icon_background_colour": None,
        "lxmf_inbound_stamp_cost": None,
        "lxmf_propagation_node_stamp_cost": None,
        "lxmf_flood_protection_enabled": False,
        "lxmf_flood_threshold_per_minute": 10,
        "lxmf_flood_max_stamp_cost": 100,
        "lxmf_flood_cooldown_seconds": 300,
        "page_archiver_enabled": False,
        "page_archiver_max_versions": 5,
        "archives_max_storage_gb": 1,
        "backup_max_count": 5,
        "crawler_enabled": False,
        "crawler_max_retries": 3,
        "crawler_retry_delay_seconds": 60,
        "crawler_max_concurrent": 1,
        "auth_enabled": False,
        "privacy_mode_enabled": False,
        "voicemail_enabled": False,
        "voicemail_greeting": None,
        "voicemail_auto_answer_delay_seconds": 5,
        "voicemail_max_recording_seconds": 60,
        "voicemail_tts_speed": 150,
        "voicemail_tts_pitch": 50,
        "voicemail_tts_voice": "en",
        "voicemail_tts_word_gap": 0,
        "custom_ringtone_enabled": False,
        "ringtone_filename": None,
        "ringtone_preferred_id": None,
        "ringtone_volume": 100,
        "map_offline_enabled": False,
        "map_mbtiles_dir": None,
        "map_tile_cache_enabled": True,
        "map_default_lat": 0.0,
        "map_default_lon": 0.0,
        "map_default_zoom": 2,
        "map_tile_server_url": None,
        "map_nominatim_api_url": None,
        "do_not_disturb_enabled": False,
        "telephone_enabled": False,
        "telephone_allow_calls_from_contacts_only": False,
        "telephone_announce_enabled": False,
        "telephone_audio_profile_id": None,
        "telephone_web_audio_enabled": False,
        "telephone_web_audio_allow_fallback": True,
        "call_recording_enabled": False,
        "block_attachments_from_strangers": False,
        "block_all_from_strangers": False,
        "show_unknown_contact_banner": True,
        "warn_on_stranger_links": True,
        "banished_effect_enabled": True,
        "banished_text": "BANISHED",
        "banished_color": "#ff0000",
        "message_font_size": 14,
        "messages_sidebar_position": "left",
        "messages_multi_pane_enabled": False,
        "nomad_tabs_enabled": False,
        "rrc_enabled": False,
        "message_icon_size": 32,
        "ui_transparency": 0,
        "ui_glass_enabled": False,
        "message_outbound_bubble_color": None,
        "message_inbound_bubble_color": None,
        "message_failed_bubble_color": None,
        "message_waiting_bubble_color": None,
        "translator_argos_enabled": False,
        "translator_libretranslate_enabled": False,
        "libretranslate_url": None,
        "libretranslate_api_key": None,
        "desktop_open_calls_in_separate_window": False,
        "desktop_hardware_acceleration_enabled": True,
        "blackhole_integration_enabled": False,
        "announce_store_lxmf_delivery": True,
        "announce_store_lxst_telephony": True,
        "announce_store_nomadnetwork_node": True,
        "announce_store_lxmf_propagation": True,
        "announce_max_stored_lxmf_delivery": 1000,
        "announce_max_stored_nomadnetwork_node": 1000,
        "announce_max_stored_lxmf_propagation": 1000,
        "announce_fetch_limit_lxmf_delivery": 200,
        "announce_fetch_limit_nomadnetwork_node": 200,
        "announce_fetch_limit_lxmf_propagation": 200,
        "announce_search_max_fetch": 2000,
        "discovered_interfaces_max_return": 100,
        "csp_extra_connect_src": "",
        "csp_extra_img_src": "",
        "csp_extra_frame_src": "",
        "csp_extra_script_src": "",
        "csp_extra_style_src": "",
        "telephone_tone_generator_enabled": True,
        "telephone_tone_generator_volume": 50,
        "location_source": "manual",
        "location_manual_lat": 0.0,
        "location_manual_lon": 0.0,
        "location_manual_alt": 0.0,
        "telemetry_enabled": False,
        "nomad_render_markdown_enabled": True,
        "nomad_render_html_enabled": False,
        "nomad_render_plaintext_enabled": True,
        "nomad_micron_wasm_enabled": False,
        "nomad_micron_default_engine": "js",
        "nomad_default_page_path": None,
        "local_message_auto_delete_enabled": False,
        "local_message_auto_delete_value": 30,
        "local_message_auto_delete_unit": "days",
        "message_blocklist_enabled": False,
    }


def config_envelope(transport: RNSTransport, overrides: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    config = build_config_dict(transport)
    if overrides:
        config.update(overrides)
    return {"config": config}


def app_info_envelope(config: AppConfig, transport: RNSTransport) -> dict[str, dict[str, Any]]:
    rns_version = _package_version("rns")
    total_paths = 0
    if transport.reticulum is not None:
        try:
            total_paths = len(transport.reticulum.get_path_table())
        except Exception:
            total_paths = 0

    storage_path = str(config.data_dir)
    database_path = str(config.data_dir / "meshchat.db")

    return {
        "app_info": {
            "version": __version__,
            "lxmf_version": "n/a (removed)",
            "rns_version": rns_version,
            "lxst_version": "n/a (removed)",
            "python_version": platform.python_version(),
            "dependencies": {
                "aiohttp": _package_version("aiohttp"),
                "rns": rns_version,
            },
            "storage_path": storage_path,
            "database_path": database_path,
            "database_file_size": 0,
            "database_files": {
                "main_bytes": 0,
                "wal_bytes": 0,
                "shm_bytes": 0,
                "total_bytes": 0,
            },
            "sqlite": {
                "journal_mode": "unknown",
                "synchronous": None,
                "wal_autocheckpoint": None,
                "busy_timeout": None,
            },
            "reticulum_config_path": str(config.rns_config_path),
            "host_platform": sys.platform,
            "is_connected_to_shared_instance": False,
            "shared_instance_address": None,
            "is_transport_enabled": transport.transport_enabled(),
            "memory_usage": {
                "rss": 0,
                "vms": 0,
            },
            "network_stats": {
                "bytes_sent": 0,
                "bytes_recv": 0,
                "packets_sent": 0,
                "packets_recv": 0,
            },
            "reticulum_stats": {
                "total_paths": total_paths,
                "announces_per_second": 0,
                "announces_per_minute": 0,
                "announces_per_hour": 0,
            },
            "is_reticulum_running": transport.is_running(),
            "download_stats": {
                "avg_download_speed_bps": None,
            },
            "emergency": False,
            "integrity_issues": [],
            "database_health_issues": [],
            "user_guidance": [],
            "tutorial_seen": False,
            "changelog_seen_version": "0.0.0",
        },
    }


def keyboard_shortcuts_response() -> dict[str, Any]:
    return {
        "type": "keyboard_shortcuts",
        "shortcuts": [],
    }


def websocket_config_message(transport: RNSTransport, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "config",
        "config": config_envelope(transport, overrides)["config"],
    }


def websocket_pong() -> dict[str, str]:
    return {"type": "pong"}


def post_ok() -> dict[str, str]:
    return {"message": "ok"}


def api_catchall_payload(path: str, method: str) -> Any:
    """Return sensible empty JSON for unmatched API routes."""
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return post_ok()

    last_segment = path.rstrip("/").rsplit("/", 1)[-1]

    list_keys = {
        "announces",
        "contacts",
        "voicemails",
        "ringtones",
        "messages",
        "backups",
        "logs",
        "attempts",
        "shortcuts",
        "interfaces",
        "peers",
        "nodes",
        "archives",
        "stickers",
        "bots",
        "hubs",
        "rooms",
        "filters",
        "exports",
        "imports",
    }
    if last_segment in list_keys or path.endswith("/folders"):
        if last_segment == "folders":
            return []
        return {last_segment: []}

    envelope_defaults: dict[str, dict[str, Any]] = {
        "contacts": {"contacts": [], "total_count": 0},
        "voicemails": {"voicemails": [], "unread_count": 0},
        "conversations": {"conversations": []},
        "notifications": notifications_response(),
        "identities": {"identities": []},
        "blocked-destinations": blocked_destinations(),
        "announce": announce_response(),
    }
    for key, payload in envelope_defaults.items():
        if key in path:
            return payload

    return {}