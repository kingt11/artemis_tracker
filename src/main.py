import asyncio
from scheduler import setup_scheduler
from config import DRY_RUN
from webhook import send_discord_message
from embeds import create_tracker_online

async def main():
    print(f"Starting Artemis II Tracker... (DRY_RUN={DRY_RUN})")
    
    # Post online message
    embed = create_tracker_online("Initializing", "Unknown", "Unknown")
    await send_discord_message("TRACKER_ONLINE", embed)
    
    setup_scheduler()
    
    # Keep the script running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
