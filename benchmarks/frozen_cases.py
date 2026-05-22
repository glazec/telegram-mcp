"""
============================================================================
  FROZEN HELD-OUT BENCHMARK   🧊  DO NOT TUNE AGAINST THESE  🧊
============================================================================
Measures GENERALIZATION. Never modify main.py's dispatcher to make a frozen
case pass. Fix failures only via algorithm/keyword improvements validated on
the ITERABLE set. See POLICY.md. Phrasings differ from iterable_cases.py.
============================================================================
"""

HELDOUT_CASES = [
    {"query": "shoot a quick text to a chat", "expected_tool": "send_message", "category": "messages"},
    {"query": "pull the latest posts from a conversation", "expected_tool": "get_messages", "category": "messages",
     "accept_alternatives": ["get_history"]},
    {"query": "queue a message to go out next week", "expected_tool": "schedule_message", "category": "messages"},
    {"query": "relay a message into a different group", "expected_tool": "forward_message", "category": "messages"},
    {"query": "fix a typo in a message I already sent", "expected_tool": "edit_message", "category": "messages"},
    {"query": "stick a message to the top of the chat", "expected_tool": "pin_message", "category": "messages"},
    {"query": "respond to a particular message in the thread", "expected_tool": "reply_to_message", "category": "messages"},
    {"query": "drop a heart emoji on a post", "expected_tool": "send_reaction", "category": "messages"},
    {"query": "stash an unsent message for later", "expected_tool": "save_draft", "category": "messages"},
    {"query": "start a survey in the group", "expected_tool": "create_poll", "category": "messages"},
    {"query": "show every dialog I have open", "expected_tool": "get_chats", "category": "chats",
     "accept_alternatives": ["list_chats"]},
    {"query": "hide a conversation in the archive", "expected_tool": "archive_chat", "category": "chats"},
    {"query": "exit this supergroup", "expected_tool": "leave_chat", "category": "chats"},
    {"query": "rename a group", "expected_tool": "edit_chat_title", "category": "chats"},
    {"query": "look through my address book", "expected_tool": "list_contacts", "category": "contacts"},
    {"query": "register a new phone number as a contact", "expected_tool": "add_contact", "category": "contacts"},
    {"query": "spin up a brand new channel", "expected_tool": "create_channel", "category": "groups"},
    {"query": "remove a troublemaker from the chat", "expected_tool": "ban_user", "category": "groups"},
    {"query": "grant admin rights to a member", "expected_tool": "promote_admin", "category": "groups"},
    {"query": "generate a join link for the group", "expected_tool": "get_invite_link", "category": "groups"},
    {"query": "attach and send a document", "expected_tool": "send_file", "category": "media"},
    {"query": "grab the attached video from a post", "expected_tool": "download_media", "category": "media"},
    {"query": "record-style audio note to a chat", "expected_tool": "send_voice", "category": "media"},
    {"query": "set a new avatar", "expected_tool": "set_profile_photo", "category": "media"},
    {"query": "edit my display name", "expected_tool": "update_profile", "category": "account"},
    {"query": "who have I blocked", "expected_tool": "get_blocked_users", "category": "account"},
    {"query": "discover a channel by its handle", "expected_tool": "search_public_chats", "category": "search"},
    {"query": "hunt for a keyword in all conversations", "expected_tool": "search_global_messages", "category": "search"},
    {"query": "turn a @handle into an id", "expected_tool": "resolve_username", "category": "search"},
    {"query": "regroup my chats under a new filter", "expected_tool": "create_folder", "category": "folders"},
]
