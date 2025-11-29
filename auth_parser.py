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

if not api_id or not api_hash or not phone:
    print("Error: Please make sure TELETHON_API_ID, TELETHON_API_HASH, and TELETHON_PHONE are set in your .env file.")
    exit(1)

async def main():
    print(f"Starting authentication for {phone}...")
    client = TelegramClient(session_name, int(api_id), api_hash)
    
    await client.start(phone=phone)
    
    print(f"\n✅ Authentication successful!")
    print(f"Session file '{session_name}.session' has been created/updated.")
    print("You can now restart your bot.")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
