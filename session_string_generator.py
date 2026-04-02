#!/usr/bin/env python3
"""
Telegram Session String Generator

This script generates a session string that can be used for Telegram authentication
with the Telegram MCP server. The session string allows for portable authentication
without storing session files.

Usage:
    python session_string_generator.py

Requirements:
    - telethon
    - python-dotenv

Note on ID Formats:
When using the MCP server, please be aware that all `chat_id` and `user_id`
parameters support integer IDs, string representations of IDs (e.g., "123456"),
and usernames (e.g., "@mychannel").
"""

import asyncio
import io
import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

load_dotenv()


def _qr_login(client: TelegramClient) -> None:
    import qrcode

    qr = client.qr_login()

    print("\n----- QR Code Login -----\n")

    qr_obj = qrcode.QRCode(border=1)
    qr_obj.add_data(qr.url)
    qr_obj.make(fit=True)
    out = io.StringIO()
    qr_obj.print_ascii(out=out, invert=True)
    print(out.getvalue())

    print("Scan the QR code above with your Telegram app:")
    print("  Open Telegram > Settings > Devices > Link Desktop Device\n")
    print(f"Or open this link on a logged-in device:\n  {qr.url}\n")
    print(f"Expires at: {qr.expires.strftime('%H:%M:%S')}")
    print("Waiting for you to scan...")

    try:
        client.loop.run_until_complete(qr.wait(timeout=120))
    except asyncio.TimeoutError:
        print("\nQR code expired. Please try again.")
        client.disconnect()
        sys.exit(1)
    except errors.SessionPasswordNeededError:
        password = input("\nTwo-factor authentication enabled. Please enter your password: ")
        client.sign_in(password=password)


def _phone_login(client: TelegramClient) -> None:
    phone = input("Please enter your phone (or bot token): ")

    try:
        client.send_code_request(phone)
    except errors.FloodWaitError as error:
        print(f"\nFlood wait error; you must wait {error.seconds} seconds before trying again.")
        client.disconnect()
        sys.exit(1)
    except errors.PhoneNumberInvalidError:
        print("\nThe phone number is invalid.")
        client.disconnect()
        sys.exit(1)
    except Exception as error:
        print(f"\nError sending code: {error}")
        client.disconnect()
        sys.exit(1)

    code = input("\nPlease enter the code you received: ")
    try:
        client.sign_in(phone, code)
    except errors.SessionPasswordNeededError:
        password = input("Two-factor authentication enabled. Please enter your password: ")
        client.sign_in(password=password)


def main() -> None:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env file")
        print("Create an .env file with your credentials from https://my.telegram.org/apps")
        sys.exit(1)

    try:
        api_id = int(api_id)
    except ValueError:
        print("Error: TELEGRAM_API_ID must be an integer")
        sys.exit(1)

    print("\n----- Telegram Session String Generator -----\n")
    print("This script will generate a session string for your Telegram account.")
    print("The generated session string can be added to your .env file.")
    print(
        "\nYour credentials will NOT be stored on any server and are only used for local authentication.\n"
    )

    print("Choose login method:")
    print("  1) QR code login (recommended)")
    print("  2) Phone number + verification code")
    method = input("\nEnter 1 or 2 [default: 1]: ").strip() or "1"

    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        client.connect()

        if not client.is_user_authorized():
            if method == "1":
                _qr_login(client)
            else:
                _phone_login(client)

        session_string = StringSession.save(client.session)

        print("\nAuthentication successful!")
        print("\n----- Your Session String -----")
        print(f"\n{session_string}\n")
        print("Add this to your .env file as:")
        print(f"TELEGRAM_SESSION_STRING={session_string}")
        print("\nIMPORTANT: Keep this string private and never share it with anyone!")

        choice = input(
            "\nWould you like to automatically update your .env file with this session string? (y/N): "
        )
        if choice.lower() == "y":
            try:
                with open(".env", "r", encoding="utf-8") as file:
                    env_contents = file.readlines()

                session_string_line_found = False
                for index, line in enumerate(env_contents):
                    if line.startswith("TELEGRAM_SESSION_STRING="):
                        env_contents[index] = f"TELEGRAM_SESSION_STRING={session_string}\n"
                        session_string_line_found = True
                        break

                if not session_string_line_found:
                    env_contents.append(f"TELEGRAM_SESSION_STRING={session_string}\n")

                with open(".env", "w", encoding="utf-8") as file:
                    file.writelines(env_contents)

                print("\n.env file updated successfully!")
            except Exception as error:
                print(f"\nError updating .env file: {error}")
                print("Please manually add the session string to your .env file.")

        client.disconnect()
    except Exception as error:
        print(f"\nError: {error}")
        print("Failed to generate session string. Please try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
