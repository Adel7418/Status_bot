import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_id = os.getenv("TELETHON_API_ID")
api_hash = os.getenv("TELETHON_API_HASH")
phone = os.getenv("TELETHON_PHONE")
session_name = os.getenv("TELETHON_SESSION_NAME", "parser_session")
session_dir = os.getenv("TELETHON_SESSION_DIR", "")

if not api_id or not api_hash or not phone:
    print("Error: Please make sure TELETHON_API_ID, TELETHON_API_HASH, and TELETHON_PHONE are set in your .env file.")
    exit(1)

# Build full session path
if session_dir:
    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, session_name)
else:
    session_path = session_name

async def main():
    print(f"Starting authentication for {phone}...")
    print(f"Session will be saved to: {session_path}.session")

    client = TelegramClient(session_path, int(api_id), api_hash)

    await client.start(phone=phone)

    print(f"\n✅ Authentication successful!")
    print(f"Session file '{session_path}.session' has been created/updated.")
    print("You can now restart your bot.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
