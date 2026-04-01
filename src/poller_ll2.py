import httpx
import asyncio
import traceback
from datetime import datetime
from config import LL2_LAUNCH_ID, YOUTUBE_FULL_URL
from state import update_state, load_state
from embeds import (
    create_status_change, create_net_shift, create_hold_update,
    create_weather_update, create_stream_live
)
from webhook import send_discord_message

async def fetch_ll2_launch():
    url = f"https://ll.thespacedevs.com/2.3.0/launches/{LL2_LAUNCH_ID}/"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"[LL2] Fetching {url}")
            response = await client.get(url)
            print(f"[LL2] Response status: {response.status_code}")
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                print(f"[LL2] Rate limited. Retry after {retry_after}s")
                await asyncio.sleep(retry_after)
                return None
            response.raise_for_status()
            data = response.json()
            print(f"[LL2] Got launch data: status={data.get('status', {}).get('name')}, net={data.get('net')}")
            return data
        except httpx.HTTPStatusError as e:
            print(f"[LL2] HTTP error {e.response.status_code}: {e.response.text[:500]}")
            return None
        except Exception as e:
            print(f"[LL2] Error fetching launch: {type(e).__name__}: {e}")
            traceback.print_exc()
            return None

async def poll_ll2():
    data = await fetch_ll2_launch()
    if not data:
        return

    state = load_state()
    
    # Extract fields
    status_id = data.get("status", {}).get("id")
    net = data.get("net")
    probability = data.get("probability")
    webcast_live = data.get("webcast_live")
    holdreason = data.get("holdreason")
    failreason = data.get("failreason")
    weather_concerns = data.get("weather_concerns")
    updates = data.get("updates", [])
    
    # Change Detection
    
    # 1. Status Changed
    if status_id != state.get("last_status_id"):
        status_name = data.get("status", {}).get("name")
        desc = data.get("status", {}).get("description")
        is_hold = status_id == 5
        is_scrub = status_id in [4, 7] # 4: Failure, 7: Partial Failure
        
        embed = create_status_change(status_name, desc, holdreason or failreason, is_hold, is_scrub)
        await send_discord_message("STATUS_CHANGE", embed)
        
        update_state("last_status_id", status_id)
        
        if is_hold:
            update_state("hold_start_utc", datetime.utcnow().isoformat() + "Z")
            # Initial hold update
            hold_embed = create_hold_update("0h 0m", holdreason)
            msg_id = await send_discord_message("HOLD_UPDATE", hold_embed)
            if msg_id:
                update_state("hold_discord_message_id", msg_id)
        elif state.get("last_status_id") == 5:
            # Lifted hold
            update_state("hold_start_utc", None)
            update_state("hold_discord_message_id", None)

    # 2. NET Shifted
    if net != state.get("last_net"):
        if state.get("last_net"):
            # Calculate delta
            pass # Simplification: Just post the shift
            embed = create_net_shift(state.get("last_net"), net, "Unknown")
            await send_discord_message("NET_SHIFT", embed)
        update_state("last_net", net)
        # TODO: Reschedule milestones
        
    # 3. Probability Changed
    if probability != state.get("last_probability"):
        embed = create_weather_update(probability, weather_concerns)
        await send_discord_message("WEATHER_UPDATE", embed)
        update_state("last_probability", probability)
        
    # 4. Webcast Went Live
    if webcast_live and not state.get("last_webcast_live"):
        thumbnail = data.get("image", {}).get("thumbnail_url")
        embed = create_stream_live(YOUTUBE_FULL_URL, thumbnail, "https://plus.nasa.gov")
        await send_discord_message("STREAM_LIVE", embed)
        update_state("last_webcast_live", webcast_live)

    # 5. Updates (45th Weather Squadron)
    max_update_id = state.get("last_ll2_update_id", 0)
    for update in updates:
        uid = update.get("id")
        if uid > max_update_id:
            info_url = update.get("info_url", "")
            if info_url and "weather" in info_url.lower():
                embed = create_weather_update(probability, weather_concerns, info_url)
                await send_discord_message("WEATHER_UPDATE", embed)
            max_update_id = uid
    update_state("last_ll2_update_id", max_update_id)

async def fetch_ll2_events():
    url = "https://ll.thespacedevs.com/2.3.0/events/upcoming/?search=artemis&limit=10"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"[LL2 Events] Fetching events...")
            response = await client.get(url)
            if response.status_code == 429:
                print("[LL2 Events] Rate limited, skipping")
                return
            response.raise_for_status()
            data = response.json()
            print(f"[LL2 Events] Got {data.get('count', 0)} events")
            
        except Exception as e:
            print(f"[LL2 Events] Error: {type(e).__name__}: {e}")
