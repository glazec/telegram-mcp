"""Tests for privacy-safe Telegram relationship metadata extraction."""

import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")

from main import (  # noqa: E402
    User,
    Chat,
    tg_types,
    build_relationship_metadata,
    collect_relationship_metadata,
    collect_group_relationship_metadata,
)


@pytest.mark.asyncio
async def test_build_relationship_metadata_excludes_private_content(
    monkeypatch,
):
    contact = User(
        id=42,
        first_name="Ada",
        last_name="Lovelace",
        username="ada",
        contact=True,
    )
    latest_outgoing = SimpleNamespace(
        date=datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc),
        out=True,
        message="this private text must never be returned",
    )
    earlier_incoming = SimpleNamespace(
        date=datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc),
        out=False,
        message="another private message",
    )

    class Client:
        def iter_messages(self, contact):
            async def messages():
                for message in [latest_outgoing, earlier_incoming]:
                    yield message

            return messages()

        async def __call__(self, request):
            return SimpleNamespace(chats=[object(), object()])

    client = Client()
    monkeypatch.setattr("main.resolve_entity", AsyncMock(return_value=contact))

    result = await build_relationship_metadata(client, contact.id)

    assert result == {
        "telegram_user_id": 42,
        "telegram_username": "ada",
        "display_name": "Ada Lovelace",
        "direct_chat_exists": True,
        "is_contact": True,
        "incoming_interaction_count": 1,
        "outgoing_interaction_count": 1,
        "last_interaction_at": "2026-09-14T12:00:00+00:00",
        "last_incoming_at": "2026-09-13T10:00:00+00:00",
        "last_outgoing_at": "2026-09-14T12:00:00+00:00",
        "shared_group_count": 2,
    }
    assert "private" not in str(result)
    assert "phone" not in str(result).lower()


@pytest.mark.asyncio
async def test_build_relationship_metadata_rejects_non_user(monkeypatch):
    monkeypatch.setattr(
        "main.resolve_entity",
        AsyncMock(return_value=SimpleNamespace(id=99, title="A group")),
    )

    with pytest.raises(Exception, match="not a user/contact"):
        await build_relationship_metadata(SimpleNamespace(), 99)


@pytest.mark.asyncio
async def test_collect_relationship_metadata_skips_self_groups_and_bots(monkeypatch):
    human = User(id=2, first_name="Human", bot=False)
    bot = User(id=3, first_name="Bot", bot=True)
    group = SimpleNamespace(id=4, title="Group")
    client = SimpleNamespace(
        get_me=AsyncMock(return_value=SimpleNamespace(id=1)),
        get_dialogs=AsyncMock(
            return_value=[
                SimpleNamespace(entity=User(id=1, first_name="Me", bot=False)),
                SimpleNamespace(entity=human),
                SimpleNamespace(entity=bot),
                SimpleNamespace(entity=group),
            ]
        ),
    )
    build = AsyncMock(return_value={"telegram_user_id": 2})
    monkeypatch.setattr("main.build_relationship_metadata", build)

    assert await collect_relationship_metadata(client, 20) == [{"telegram_user_id": 2}]
    build.assert_awaited_once_with(client, 2)


@pytest.mark.asyncio
async def test_group_metadata_stores_only_direct_reply_connections(monkeypatch):
    group = Chat(
        id=100,
        title="Approved group",
        photo=tg_types.ChatPhotoEmpty(),
        participants_count=20,
        date=None,
        version=1,
    )
    person = User(id=2, first_name="Ada", username="ada", bot=False)
    messages = [
        SimpleNamespace(
            id=3,
            sender_id=2,
            reply_to_msg_id=2,
            date=datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc),
            message="private reply text",
        ),
        SimpleNamespace(
            id=2,
            sender_id=1,
            reply_to_msg_id=1,
            date=datetime(2026, 9, 14, 11, 0, tzinfo=timezone.utc),
            message="private member text",
        ),
        SimpleNamespace(
            id=1,
            sender_id=2,
            reply_to_msg_id=None,
            date=datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc),
            message="private original text",
        ),
    ]

    class Client:
        get_me = AsyncMock(return_value=SimpleNamespace(id=1))

        def iter_messages(self, entity, limit):
            async def iterate():
                for message in messages:
                    yield message

            return iterate()

    resolve = AsyncMock(side_effect=[group, person])
    monkeypatch.setattr("main.resolve_entity", resolve)

    result = await collect_group_relationship_metadata(Client(), [100], "Darko", 100)

    assert result["connections"] == [
        {
            "iosg_member": "Darko",
            "telegram_user_id": 2,
            "telegram_group_id": 100,
            "replies_from_member": 1,
            "replies_to_member": 1,
            "last_interaction_at": "2026-09-14T12:00:00+00:00",
        }
    ]
    assert "private" not in str(result)
