"""Unit tests for RNSVG Phase 2 messaging."""

from __future__ import annotations

import tempfile
from pathlib import Path

from rnsvg.database import MessageDatabase
from rnsvg.messaging import MessageManager


def test_conversation_pagination_desc_after_id():
    with tempfile.TemporaryDirectory() as tmp:
        db = MessageDatabase(Path(tmp) / "messages.db")
        local = "a" * 32
        peer = "b" * 32
        ids = []
        for i in range(5):
            row = db.insert_message(
                source_hash=local,
                destination_hash=peer,
                direction="outbound",
                content=f"msg-{i}",
                state="sent",
            )
            ids.append(row["id"])

        page = db.get_conversation_messages(local, peer, limit=2, order="desc", after_id=ids[-1])
        assert len(page) == 2
        assert page[0]["content"] == "msg-2"
        assert page[1]["content"] == "msg-3"


def test_to_lxmf_api_dict_includes_incoming_flag():
    with tempfile.TemporaryDirectory() as tmp:
        db = MessageDatabase(Path(tmp) / "messages.db")
        mgr = MessageManager(database=db)
        local = "c" * 32
        peer = "d" * 32
        inbound = db.insert_message(
            source_hash=peer,
            destination_hash=local,
            direction="inbound",
            content="hello",
            state="delivered",
        )
        api = mgr.to_lxmf_api_dict(inbound, local)
        assert api["is_incoming"] is True
        assert api["is_outbound"] is False
        assert api["id"] == inbound["id"]


def test_resolve_source_from_payload():
    with tempfile.TemporaryDirectory() as tmp:
        db = MessageDatabase(Path(tmp) / "messages.db")
        mgr = MessageManager(database=db)
        node = "e" * 32
        payload = {"type": "text", "content": "hi", "source_node_hash": node}
        assert mgr._resolve_source_node_hash(payload, object()) == node