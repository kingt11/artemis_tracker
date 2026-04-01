import asyncio
from scheduler import setup_scheduler
from config import DRY_RUN, CONFIRMED_NET, YOUTUBE_FULL_URL
from poller_ll2 import fetch_ll2_launch
from webhook import send_discord_message
from embeds import create_tracker_online

async def main():
    print(f"Starting Artemis II Tracker... (DRY_RUN={DRY_RUN})")
    
    # Fetch initial data for the startup embed
    data = await fetch_ll2_launch()
    if data:
        status = data.get("status", {}).get("name", "Unknown")
        net = data.get("net", CONFIRMED_NET)
    else:
        status = "API unavailable - using cached NET"
        net = CONFIRMED_NET
    
    embed = create_tracker_online(status, net, f"[YouTube]({YOUTUBE_FULL_URL})")
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
