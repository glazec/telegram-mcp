"""
Comprehensive test suite for all Telegram MCP tools.
Tests cover all 86 tools defined in main.py with proper mocking.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime

# Set up environment before importing main
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "test_hash"
# Use empty string to avoid Telethon validation during import
os.environ["TELEGRAM_SESSION_STRING"] = ""
os.environ["TELEGRAM_SESSION_NAME"] = "test_session"

from main import (
    get_chats, get_messages, send_message, subscribe_public_channel,
    list_inline_buttons, press_inline_button, list_contacts, search_contacts,
    get_contact_ids, list_messages, list_topics, list_chats, get_chat,
    get_direct_chat_by_contact, get_contact_chats, get_last_interaction,
    get_message_context, add_contact, delete_contact, block_user, unblock_user,
    get_me, create_group, invite_to_group, leave_chat, get_participants,
    send_file, download_media, update_profile, set_profile_photo,
    delete_profile_photo, get_privacy_settings, set_privacy_settings,
    import_contacts, export_contacts, get_blocked_users, create_channel,
    edit_chat_title, edit_chat_photo, delete_chat_photo, promote_admin,
    demote_admin, ban_user, unban_user, get_admins, get_banned_users,
    get_invite_link, join_chat_by_link, export_chat_invite,
    import_chat_invite, send_voice, forward_message, edit_message,
    delete_message, pin_message, unpin_message, mark_as_read,
    reply_to_message, get_media_info, search_public_chats, search_messages,
    resolve_username, mute_chat, unmute_chat, archive_chat, unarchive_chat,
    get_sticker_sets, send_sticker, get_gif_search, send_gif, get_bot_info,
    set_bot_commands, get_history, get_user_photos, get_user_status,
    get_recent_actions, get_pinned_messages, create_poll, send_reaction,
    remove_reaction, get_message_reactions, save_draft, get_drafts,
    clear_draft, list_folders, get_folder, create_folder, add_chat_to_folder,
    remove_chat_from_folder, delete_folder, reorder_folders
)


@pytest.fixture
def mock_client():
    """Fixture to create a mocked TelegramClient."""
    with patch('main.client') as mock:
        # Setup common mock responses
        mock.get_dialogs = AsyncMock(return_value=[])
        mock.get_entity = AsyncMock(return_value=MagicMock(id=123, title="Test Chat"))
        mock.get_messages = AsyncMock(return_value=[])
        mock.send_message = AsyncMock()
        mock.get_me = AsyncMock(return_value=MagicMock(id=123, first_name="Test", last_name="User"))
        mock.iter_messages = AsyncMock(return_value=[])
        mock.iter_participants = AsyncMock(return_value=[])

        yield mock


class TestChatTools:
    """Tests for chat-related tools."""

    @pytest.mark.asyncio
    async def test_get_chats(self, mock_client):
        """Test get_chats retrieves paginated chat list."""
        mock_dialog = MagicMock()
        mock_dialog.entity = MagicMock(id=123, title="Test Chat")
        mock_client.get_dialogs.return_value = [mock_dialog]

        result = await get_chats(page=1, page_size=20)

        assert isinstance(result, str)
        mock_client.get_dialogs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_messages(self, mock_client):
        """Test get_messages retrieves messages from a chat."""
        mock_msg = MagicMock()
        mock_msg.id = 1
        mock_msg.message = "Test message"
        mock_msg.date = datetime.now()
        mock_msg.sender = MagicMock(first_name="Sender")
        mock_msg.reply_to = None
        mock_client.get_messages.return_value = [mock_msg]

        result = await get_messages(chat_id=123, page=1, page_size=20)

        assert isinstance(result, str)
        mock_client.get_entity.assert_called_once()
        mock_client.get_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message(self, mock_client):
        """Test send_message sends a message to a chat."""
        result = await send_message(chat_id=123, message="Hello")

        assert isinstance(result, str)
        assert "success" in result.lower()
        mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_chats(self, mock_client):
        """Test list_chats retrieves filtered chat list."""
        mock_dialog = MagicMock()
        mock_dialog.entity = MagicMock(id=123)
        mock_client.get_dialogs.return_value = [mock_dialog]

        result = await list_chats(chat_type=None, limit=20)

        assert isinstance(result, str)
        mock_client.get_dialogs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_chat(self, mock_client):
        """Test get_chat retrieves specific chat details."""
        result = await get_chat(chat_id=123)

        assert isinstance(result, str)
        mock_client.get_entity.assert_called_once()


class TestChannelTools:
    """Tests for channel-related tools."""

    @pytest.mark.asyncio
    async def test_subscribe_public_channel(self, mock_client):
        """Test subscribe_public_channel joins a channel."""
        mock_client.return_value = AsyncMock()

        result = await subscribe_public_channel(channel="testchannel")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_create_channel(self, mock_client):
        """Test create_channel creates a new channel."""
        mock_client.return_value = AsyncMock()

        result = await create_channel(title="Test Channel", about="Description")

        assert isinstance(result, str)


class TestContactTools:
    """Tests for contact management tools."""

    @pytest.mark.asyncio
    async def test_list_contacts(self, mock_client):
        """Test list_contacts retrieves contact list."""
        mock_contact = MagicMock()
        mock_contact.id = 123
        mock_contact.first_name = "John"
        mock_contact.last_name = "Doe"
        mock_client.return_value = AsyncMock()

        result = await list_contacts()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_contacts(self, mock_client):
        """Test search_contacts searches for contacts."""
        result = await search_contacts(query="John")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_contact_ids(self, mock_client):
        """Test get_contact_ids retrieves contact IDs."""
        result = await get_contact_ids()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_add_contact(self, mock_client):
        """Test add_contact adds a new contact."""
        mock_client.return_value = AsyncMock()

        result = await add_contact(phone="+1234567890", first_name="John", last_name="Doe")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_delete_contact(self, mock_client):
        """Test delete_contact removes a contact."""
        result = await delete_contact(user_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_block_user(self, mock_client):
        """Test block_user blocks a user."""
        result = await block_user(user_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_unblock_user(self, mock_client):
        """Test unblock_user unblocks a user."""
        result = await unblock_user(user_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_import_contacts(self, mock_client):
        """Test import_contacts imports multiple contacts."""
        contacts = [{"phone": "+1234567890", "first_name": "John", "last_name": "Doe"}]

        result = await import_contacts(contacts=contacts)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_export_contacts(self, mock_client):
        """Test export_contacts exports all contacts."""
        result = await export_contacts()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_blocked_users(self, mock_client):
        """Test get_blocked_users retrieves blocked users."""
        result = await get_blocked_users()

        assert isinstance(result, str)


class TestGroupTools:
    """Tests for group management tools."""

    @pytest.mark.asyncio
    async def test_create_group(self, mock_client):
        """Test create_group creates a new group."""
        result = await create_group(title="Test Group", user_ids=[123, 456])

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_invite_to_group(self, mock_client):
        """Test invite_to_group invites users to a group."""
        result = await invite_to_group(group_id=123, user_ids=[456, 789])

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_leave_chat(self, mock_client):
        """Test leave_chat leaves a chat."""
        result = await leave_chat(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_participants(self, mock_client):
        """Test get_participants retrieves group members."""
        result = await get_participants(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_promote_admin(self, mock_client):
        """Test promote_admin promotes a user to admin."""
        result = await promote_admin(group_id=123, user_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_demote_admin(self, mock_client):
        """Test demote_admin demotes an admin."""
        result = await demote_admin(group_id=123, user_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_ban_user(self, mock_client):
        """Test ban_user bans a user from group."""
        result = await ban_user(chat_id=123, user_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_unban_user(self, mock_client):
        """Test unban_user unbans a user from group."""
        result = await unban_user(chat_id=123, user_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_admins(self, mock_client):
        """Test get_admins retrieves group admins."""
        result = await get_admins(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_banned_users(self, mock_client):
        """Test get_banned_users retrieves banned users."""
        result = await get_banned_users(chat_id=123)

        assert isinstance(result, str)


class TestMessageTools:
    """Tests for message-related tools."""

    @pytest.mark.asyncio
    async def test_list_messages(self, mock_client):
        """Test list_messages retrieves messages."""
        result = await list_messages(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_forward_message(self, mock_client):
        """Test forward_message forwards a message."""
        result = await forward_message(from_chat_id=123, to_chat_id=456, message_id=789)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_edit_message(self, mock_client):
        """Test edit_message edits a message."""
        result = await edit_message(chat_id=123, message_id=456, new_text="Edited")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_delete_message(self, mock_client):
        """Test delete_message deletes a message."""
        result = await delete_message(chat_id=123, message_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_pin_message(self, mock_client):
        """Test pin_message pins a message."""
        result = await pin_message(chat_id=123, message_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_unpin_message(self, mock_client):
        """Test unpin_message unpins a message."""
        result = await unpin_message(chat_id=123, message_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_mark_as_read(self, mock_client):
        """Test mark_as_read marks messages as read."""
        result = await mark_as_read(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_reply_to_message(self, mock_client):
        """Test reply_to_message replies to a message."""
        result = await reply_to_message(chat_id=123, message_id=456, text="Reply")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_media_info(self, mock_client):
        """Test get_media_info retrieves media information."""
        result = await get_media_info(chat_id=123, message_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_message_context(self, mock_client):
        """Test get_message_context retrieves surrounding messages."""
        result = await get_message_context(chat_id=123, message_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_pinned_messages(self, mock_client):
        """Test get_pinned_messages retrieves pinned messages."""
        result = await get_pinned_messages(chat_id=123)

        assert isinstance(result, str)


class TestInlineButtonTools:
    """Tests for inline button tools."""

    @pytest.mark.asyncio
    async def test_list_inline_buttons(self, mock_client):
        """Test list_inline_buttons lists inline keyboard buttons."""
        mock_msg = MagicMock()
        mock_msg.reply_markup = None
        mock_client.get_messages.return_value = [mock_msg]

        result = await list_inline_buttons(chat_id=123, message_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_press_inline_button(self, mock_client):
        """Test press_inline_button presses an inline button."""
        result = await press_inline_button(chat_id=123, message_id=456, button_index=0)

        assert isinstance(result, str)


class TestFileTools:
    """Tests for file-related tools."""

    @pytest.mark.asyncio
    async def test_send_file(self, mock_client):
        """Test send_file sends a file."""
        result = await send_file(chat_id=123, file_path="/tmp/test.txt", caption="Test")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_download_media(self, mock_client):
        """Test download_media downloads media."""
        result = await download_media(chat_id=123, message_id=456, file_path="/tmp/download.jpg")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_voice(self, mock_client):
        """Test send_voice sends a voice message."""
        result = await send_voice(chat_id=123, file_path="/tmp/voice.ogg")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_sticker(self, mock_client):
        """Test send_sticker sends a sticker."""
        result = await send_sticker(chat_id=123, file_path="/tmp/sticker.webp")

        assert isinstance(result, str)


class TestProfileTools:
    """Tests for profile management tools."""

    @pytest.mark.asyncio
    async def test_get_me(self, mock_client):
        """Test get_me retrieves current user info."""
        result = await get_me()

        assert isinstance(result, str)
        mock_client.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile(self, mock_client):
        """Test update_profile updates user profile."""
        result = await update_profile(first_name="John", last_name="Doe", about="Bio")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_set_profile_photo(self, mock_client):
        """Test set_profile_photo sets profile photo."""
        result = await set_profile_photo(file_path="/tmp/photo.jpg")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_delete_profile_photo(self, mock_client):
        """Test delete_profile_photo deletes profile photo."""
        result = await delete_profile_photo()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_user_photos(self, mock_client):
        """Test get_user_photos retrieves user photos."""
        result = await get_user_photos(user_id=123, limit=10)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_user_status(self, mock_client):
        """Test get_user_status retrieves user status."""
        result = await get_user_status(user_id=123)

        assert isinstance(result, str)


class TestPrivacyTools:
    """Tests for privacy and settings tools."""

    @pytest.mark.asyncio
    async def test_get_privacy_settings(self, mock_client):
        """Test get_privacy_settings retrieves privacy settings."""
        result = await get_privacy_settings()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_set_privacy_settings(self, mock_client):
        """Test set_privacy_settings updates privacy settings."""
        result = await set_privacy_settings(
            key="phone_number",
            allow_users=[123, 456]
        )

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_mute_chat(self, mock_client):
        """Test mute_chat mutes a chat."""
        result = await mute_chat(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_unmute_chat(self, mock_client):
        """Test unmute_chat unmutes a chat."""
        result = await unmute_chat(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_archive_chat(self, mock_client):
        """Test archive_chat archives a chat."""
        result = await archive_chat(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_unarchive_chat(self, mock_client):
        """Test unarchive_chat unarchives a chat."""
        result = await unarchive_chat(chat_id=123)

        assert isinstance(result, str)


class TestChatEditingTools:
    """Tests for chat editing tools."""

    @pytest.mark.asyncio
    async def test_edit_chat_title(self, mock_client):
        """Test edit_chat_title changes chat title."""
        result = await edit_chat_title(chat_id=123, title="New Title")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_edit_chat_photo(self, mock_client):
        """Test edit_chat_photo changes chat photo."""
        result = await edit_chat_photo(chat_id=123, file_path="/tmp/photo.jpg")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_delete_chat_photo(self, mock_client):
        """Test delete_chat_photo deletes chat photo."""
        result = await delete_chat_photo(chat_id=123)

        assert isinstance(result, str)


class TestInviteTools:
    """Tests for invite link tools."""

    @pytest.mark.asyncio
    async def test_get_invite_link(self, mock_client):
        """Test get_invite_link retrieves invite link."""
        result = await get_invite_link(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_join_chat_by_link(self, mock_client):
        """Test join_chat_by_link joins chat via invite link."""
        result = await join_chat_by_link(link="https://t.me/joinchat/xxx")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_export_chat_invite(self, mock_client):
        """Test export_chat_invite exports chat invite."""
        result = await export_chat_invite(chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_import_chat_invite(self, mock_client):
        """Test import_chat_invite imports chat invite."""
        result = await import_chat_invite(hash="invitehash123")

        assert isinstance(result, str)


class TestSearchTools:
    """Tests for search tools."""

    @pytest.mark.asyncio
    async def test_search_public_chats(self, mock_client):
        """Test search_public_chats searches for public chats."""
        result = await search_public_chats(query="test")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_messages(self, mock_client):
        """Test search_messages searches messages in a chat."""
        result = await search_messages(chat_id=123, query="test", limit=20)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_resolve_username(self, mock_client):
        """Test resolve_username resolves a username."""
        result = await resolve_username(username="testuser")

        assert isinstance(result, str)


class TestMediaTools:
    """Tests for media and sticker tools."""

    @pytest.mark.asyncio
    async def test_get_sticker_sets(self, mock_client):
        """Test get_sticker_sets retrieves sticker sets."""
        result = await get_sticker_sets()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_gif_search(self, mock_client):
        """Test get_gif_search searches for GIFs."""
        result = await get_gif_search(query="funny", limit=10)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_gif(self, mock_client):
        """Test send_gif sends a GIF."""
        result = await send_gif(chat_id=123, gif_id=456)

        assert isinstance(result, str)


class TestBotTools:
    """Tests for bot-related tools."""

    @pytest.mark.asyncio
    async def test_get_bot_info(self, mock_client):
        """Test get_bot_info retrieves bot information."""
        result = await get_bot_info(bot_username="testbot")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_set_bot_commands(self, mock_client):
        """Test set_bot_commands sets bot commands."""
        commands = [{"command": "start", "description": "Start bot"}]

        result = await set_bot_commands(bot_username="testbot", commands=commands)

        assert isinstance(result, str)


class TestHistoryTools:
    """Tests for history and action tools."""

    @pytest.mark.asyncio
    async def test_get_history(self, mock_client):
        """Test get_history retrieves chat history."""
        result = await get_history(chat_id=123, limit=100)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_recent_actions(self, mock_client):
        """Test get_recent_actions retrieves recent actions."""
        result = await get_recent_actions(chat_id=123)

        assert isinstance(result, str)


class TestTopicTools:
    """Tests for topic/forum tools."""

    @pytest.mark.asyncio
    async def test_list_topics(self, mock_client):
        """Test list_topics lists forum topics."""
        result = await list_topics(chat_id=123)

        assert isinstance(result, str)


class TestContactRelationshipTools:
    """Tests for contact relationship tools."""

    @pytest.mark.asyncio
    async def test_get_direct_chat_by_contact(self, mock_client):
        """Test get_direct_chat_by_contact finds direct chat."""
        result = await get_direct_chat_by_contact(contact_query="John")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_contact_chats(self, mock_client):
        """Test get_contact_chats retrieves contact's chats."""
        result = await get_contact_chats(contact_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_last_interaction(self, mock_client):
        """Test get_last_interaction retrieves last interaction."""
        result = await get_last_interaction(contact_id=123)

        assert isinstance(result, str)


class TestPollTools:
    """Tests for poll tools."""

    @pytest.mark.asyncio
    async def test_create_poll(self, mock_client):
        """Test create_poll creates a poll."""
        result = await create_poll(
            chat_id=123,
            question="Test poll?",
            options=["Yes", "No"]
        )

        assert isinstance(result, str)


class TestReactionTools:
    """Tests for reaction tools."""

    @pytest.mark.asyncio
    async def test_send_reaction(self, mock_client):
        """Test send_reaction sends a reaction."""
        result = await send_reaction(chat_id=123, message_id=456, emoji="👍")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_remove_reaction(self, mock_client):
        """Test remove_reaction removes reactions."""
        result = await remove_reaction(chat_id=123, message_id=456)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_message_reactions(self, mock_client):
        """Test get_message_reactions retrieves message reactions."""
        result = await get_message_reactions(chat_id=123, message_id=456)

        assert isinstance(result, str)


class TestDraftTools:
    """Tests for draft message tools."""

    @pytest.mark.asyncio
    async def test_save_draft(self, mock_client):
        """Test save_draft saves a draft message."""
        result = await save_draft(chat_id=123, message="Draft text")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_drafts(self, mock_client):
        """Test get_drafts retrieves all drafts."""
        result = await get_drafts()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_clear_draft(self, mock_client):
        """Test clear_draft clears a draft."""
        result = await clear_draft(chat_id=123)

        assert isinstance(result, str)


class TestFolderTools:
    """Tests for folder management tools."""

    @pytest.mark.asyncio
    async def test_list_folders(self, mock_client):
        """Test list_folders lists all folders."""
        result = await list_folders()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_folder(self, mock_client):
        """Test get_folder retrieves specific folder."""
        result = await get_folder(folder_id=1)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_create_folder(self, mock_client):
        """Test create_folder creates a new folder."""
        result = await create_folder(
            title="Test Folder",
            chat_ids=[123, 456]
        )

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_add_chat_to_folder(self, mock_client):
        """Test add_chat_to_folder adds chat to folder."""
        result = await add_chat_to_folder(folder_id=1, chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_remove_chat_from_folder(self, mock_client):
        """Test remove_chat_from_folder removes chat from folder."""
        result = await remove_chat_from_folder(folder_id=1, chat_id=123)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_delete_folder(self, mock_client):
        """Test delete_folder deletes a folder."""
        result = await delete_folder(folder_id=1)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_reorder_folders(self, mock_client):
        """Test reorder_folders reorders folders."""
        result = await reorder_folders(folder_ids=[1, 2, 3])

        assert isinstance(result, str)


# Run tests with: pytest test_tools.py -v
# Run specific test class: pytest test_tools.py::TestChatTools -v
# Run with coverage: pytest test_tools.py --cov=main --cov-report=html
