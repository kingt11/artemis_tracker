import httpx
import time
import asyncio
from config import (
    DISCORD_WEBHOOK_ALERTS,
    DISCORD_WEBHOOK_MISSION,
    DISCORD_WEBHOOK_NEWS,
    DRY_RUN,
    DISCORD_ROLE_ID
)

# Routing Table
# Embed Type -> (Webhook URL, Role Ping?)
ROUTING_TABLE = {
    "TRACKER_ONLINE": (DISCORD_WEBHOOK_ALERTS, False),
    "CREW_INTRO": (DISCORD_WEBHOOK_MISSION, False),
    "LAUNCH_COUNTDOWN": (DISCORD_WEBHOOK_MISSION, False),
    "STATUS_CHANGE": (DISCORD_WEBHOOK_ALERTS, True),
    "HOLD_UPDATE": (DISCORD_WEBHOOK_ALERTS, True), # Role ping on initial POST only
    "NET_SHIFT": (DISCORD_WEBHOOK_ALERTS, True),
    "STREAM_LIVE": (DISCORD_WEBHOOK_ALERTS, True),
    "WEATHER_UPDATE": (DISCORD_WEBHOOK_MISSION, False),
    "MILESTONE": (DISCORD_WEBHOOK_MISSION, False),
    "HISTORICAL_MILESTONE": (DISCORD_WEBHOOK_MISSION, False),
    "MISSION_DAY": (DISCORD_WEBHOOK_MISSION, False),
    "MISSION_EVENT": (DISCORD_WEBHOOK_NEWS, False),
    "NEWS": (DISCORD_WEBHOOK_NEWS, False),
    "SPLASHDOWN": (DISCORD_WEBHOOK_ALERTS, True),
}

last_post_time = {}

async def send_discord_message(embed_type, embed_payload, message_id=None, is_patch=False):
    if embed_type not in ROUTING_TABLE:
        print(f"Unknown embed type: {embed_type}")
        return None

    webhook_url, role_ping = ROUTING_TABLE[embed_type]
    
    if not webhook_url:
        print(f"No webhook URL configured for {embed_type}")
        return None

    # Rate limiting: 1 second delay per webhook
    now = time.time()
    if webhook_url in last_post_time:
        elapsed = now - last_post_time[webhook_url]
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
    
    last_post_time[webhook_url] = time.time()

    payload = {"embeds": [embed_payload]}
    
    if role_ping and not is_patch and DISCORD_ROLE_ID:
        payload["content"] = f"<@&{DISCORD_ROLE_ID}>"

    if DRY_RUN:
        print(f"[DRY RUN] Would {'PATCH' if is_patch else 'POST'} to {embed_type} webhook:")
        print(payload)
        return "dry_run_message_id"

    async with httpx.AsyncClient() as client:
        try:
            if is_patch and message_id:
                url = f"{webhook_url}/messages/{message_id}"
                response = await client.patch(url, json=payload)
            else:
                url = f"{webhook_url}?wait=true" # wait=true returns the message object
                response = await client.post(url, json=payload)
            
            response.raise_for_status()
            
            if response.status_code in (200, 201):
                data = response.json()
                return data.get("id")
            return None
        except Exception as e:
            print(f"Error sending Discord message: {e}")
            return None
