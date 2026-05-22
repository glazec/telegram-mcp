"""
============================================================================
  ITERABLE BENCHMARK   ✏  OK to add/modify/paraphrase cases  ✏
============================================================================
Development feedback set for the Telegram MCP search/execute dispatcher
(`_dsp_search` in main.py). MAY be tuned to pass these. See POLICY.md.
For honest generalization, use frozen_cases.py (never tune against it).
============================================================================
"""

BENCHMARK_CASES = [
    # messages
    {"query": "send a message to a chat", "expected_tool": "send_message", "category": "messages"},
    {"query": "get recent messages from a chat", "expected_tool": "get_messages", "category": "messages"},
    {"query": "schedule a message for later", "expected_tool": "schedule_message", "category": "messages"},
    {"query": "forward a message to another chat", "expected_tool": "forward_message", "category": "messages"},
    {"query": "edit a message I sent", "expected_tool": "edit_message", "category": "messages"},
    {"query": "delete a message", "expected_tool": "delete_message", "category": "messages"},
    {"query": "pin a message in a chat", "expected_tool": "pin_message", "category": "messages"},
    {"query": "reply to a specific message", "expected_tool": "reply_to_message", "category": "messages"},
    {"query": "mark messages as read", "expected_tool": "mark_as_read", "category": "messages"},
    {"query": "react to a message with an emoji", "expected_tool": "send_reaction", "category": "messages"},
    {"query": "save a draft message", "expected_tool": "save_draft", "category": "messages"},
    {"query": "create a poll in a chat", "expected_tool": "create_poll", "category": "messages"},
    {"query": "get full chat history", "expected_tool": "get_history", "category": "messages"},
    {"query": "search for messages in a chat", "expected_tool": "search_messages", "category": "messages"},
    # chats
    {"query": "list all my chats", "expected_tool": "get_chats", "category": "chats",
     "accept_alternatives": ["list_chats"]},
    {"query": "get details about a chat", "expected_tool": "get_chat", "category": "chats"},
    {"query": "mute notifications for a chat", "expected_tool": "mute_chat", "category": "chats"},
    {"query": "archive a chat", "expected_tool": "archive_chat", "category": "chats"},
    {"query": "leave a group or channel", "expected_tool": "leave_chat", "category": "chats"},
    {"query": "edit the title of a chat", "expected_tool": "edit_chat_title", "category": "chats"},
    {"query": "list forum topics in a supergroup", "expected_tool": "list_topics", "category": "chats"},
    # contacts
    {"query": "list all my contacts", "expected_tool": "list_contacts", "category": "contacts"},
    {"query": "search my contacts by name", "expected_tool": "search_contacts", "category": "contacts"},
    {"query": "add a new contact", "expected_tool": "add_contact", "category": "contacts"},
    {"query": "delete a contact", "expected_tool": "delete_contact", "category": "contacts"},
    # groups
    {"query": "create a new group", "expected_tool": "create_group", "category": "groups"},
    {"query": "create a new channel", "expected_tool": "create_channel", "category": "groups"},
    {"query": "ban a user from a group", "expected_tool": "ban_user", "category": "groups"},
    {"query": "promote a user to admin", "expected_tool": "promote_admin", "category": "groups"},
    {"query": "list participants in a group", "expected_tool": "get_participants", "category": "groups"},
    {"query": "get the invite link for a group", "expected_tool": "get_invite_link", "category": "groups"},
    {"query": "invite users to a group", "expected_tool": "invite_to_group", "category": "groups"},
    {"query": "get the admin action log", "expected_tool": "get_recent_actions", "category": "groups"},
    # media
    {"query": "send a file to a chat", "expected_tool": "send_file", "category": "media"},
    {"query": "download media from a message", "expected_tool": "download_media", "category": "media"},
    {"query": "send a voice message", "expected_tool": "send_voice", "category": "media"},
    {"query": "send a sticker", "expected_tool": "send_sticker", "category": "media"},
    {"query": "search for a gif", "expected_tool": "get_gif_search", "category": "media"},
    # account
    {"query": "update my profile name and bio", "expected_tool": "update_profile", "category": "account"},
    {"query": "get my own user info", "expected_tool": "get_me", "category": "account"},
    {"query": "get my privacy settings", "expected_tool": "get_privacy_settings", "category": "account"},
    {"query": "list blocked users", "expected_tool": "get_blocked_users", "category": "account"},
    # search
    {"query": "search public channels and bots", "expected_tool": "search_public_chats", "category": "search"},
    {"query": "search all my messages globally", "expected_tool": "search_global_messages", "category": "search"},
    {"query": "resolve a username to an id", "expected_tool": "resolve_username", "category": "search"},
    # folders
    {"query": "list my dialog folders", "expected_tool": "list_folders", "category": "folders"},
    {"query": "create a new folder", "expected_tool": "create_folder", "category": "folders"},
    {"query": "add a chat to a folder", "expected_tool": "add_chat_to_folder", "category": "folders"},
]

REAL_WORLD_CASES = [
    {"query": "dm someone on telegram", "expected_tool": "send_message", "category": "messages"},
    {"query": "what did they say in this chat recently", "expected_tool": "get_messages", "category": "messages",
     "accept_alternatives": ["get_history"]},
    {"query": "send this message tomorrow morning", "expected_tool": "schedule_message", "category": "messages"},
    {"query": "remove a message I sent by mistake", "expected_tool": "delete_message", "category": "messages"},
    {"query": "thumbs up this message", "expected_tool": "send_reaction", "category": "messages"},
    {"query": "show me all my conversations", "expected_tool": "get_chats", "category": "chats",
     "accept_alternatives": ["list_chats"]},
    {"query": "silence notifications from this group", "expected_tool": "mute_chat", "category": "chats"},
    {"query": "kick this member out of the group", "expected_tool": "ban_user", "category": "groups"},
    {"query": "make this person a moderator", "expected_tool": "promote_admin", "category": "groups"},
    {"query": "who is in this group", "expected_tool": "get_participants", "category": "groups"},
    {"query": "upload a document to the chat", "expected_tool": "send_file", "category": "media"},
    {"query": "save the photo from this message", "expected_tool": "download_media", "category": "media"},
    {"query": "find people to message", "expected_tool": "search_contacts", "category": "contacts",
     "accept_alternatives": ["list_contacts"]},
    {"query": "change my bio", "expected_tool": "update_profile", "category": "account"},
    {"query": "look up tweets... I mean find a public channel by name", "expected_tool": "search_public_chats", "category": "search"},
    {"query": "search across every chat for a keyword", "expected_tool": "search_global_messages", "category": "search"},
    {"query": "organize chats into a new folder", "expected_tool": "create_folder", "category": "folders"},
    {"query": "is this person online right now", "expected_tool": "get_user_status", "category": "account"},
]


def score_case(case: dict, predicted_tool: str) -> dict:
    expected = case["expected_tool"]
    alts = set(case.get("accept_alternatives", [])) | {expected}
    return {"tool_correct": predicted_tool in alts, "expected": expected, "got": predicted_tool}
