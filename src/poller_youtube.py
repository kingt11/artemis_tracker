import httpx
from config import YOUTUBE_API_KEY, YOUTUBE_VIDEO_ID, YOUTUBE_FULL_URL, NASA_PLUS_URL
from state import load_state, update_state
from embeds import create_stream_live
from webhook import send_discord_message

async def poll_youtube():
    if not YOUTUBE_API_KEY:
        return
        
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id={YOUTUBE_VIDEO_ID}&key={YOUTUBE_API_KEY}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if not items:
                return
                
            item = items[0]
            snippet = item.get("snippet", {})
            live_details = item.get("liveStreamingDetails", {})
            
            is_live = snippet.get("liveBroadcastContent") == "live"
            viewers = live_details.get("concurrentViewers")
            
            state = load_state()
            if is_live and not state.get("last_webcast_live"):
                thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url")
                embed = create_stream_live(YOUTUBE_FULL_URL, thumbnail, NASA_PLUS_URL, viewers)
                await send_discord_message("STREAM_LIVE", embed)
                update_state("last_webcast_live", True)
                
        except Exception as e:
            print(f"Error fetching YouTube data: {e}")
