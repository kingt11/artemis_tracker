import os
from dotenv import load_dotenv

load_dotenv()

# Constants
LL2_LAUNCH_ID = "41699701-2ef4-4b0c-ac9d-6757820cde87"
YOUTUBE_VIDEO_ID = "Tf_UjBMIzNo"
NASA_YOUTUBE_CHANNEL_ID = "UCLA_DiR1FfKNvjuUpBHmylQ"
CONFIRMED_NET = "2026-04-01T22:24:00Z"

# Environment Variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DISCORD_WEBHOOK_ALERTS = os.getenv("DISCORD_WEBHOOK_ALERTS")
DISCORD_WEBHOOK_MISSION = os.getenv("DISCORD_WEBHOOK_MISSION")
DISCORD_WEBHOOK_NEWS = os.getenv("DISCORD_WEBHOOK_NEWS")
DISCORD_ROLE_ID = os.getenv("DISCORD_ROLE_ID")
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", "state.json")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Asset URLs
MISSION_PATCH_URL = "https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/mission_patch_images/artemis2520ii_mission_patch_20250404074145.png"
LAUNCH_THUMBNAIL_URL = "https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/images/255bauto255d__image_thumbnail_20240305193913.jpeg"
INFOGRAPHIC_URL = "https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/infographic_images/sls2520block2_infographic_20260329082241.jpeg"
FLIGHTCLUB_URL = "https://flightclub.io/result?llId=41699701-2ef4-4b0c-ac9d-6757820cde87"
NASA_PLUS_URL = "https://plus.nasa.gov/scheduled-video/nasas-artemis-ii-crew-launches-to-the-moon-official-broadcast/"
YOUTUBE_FULL_URL = f"https://www.youtube.com/watch?v={YOUTUBE_VIDEO_ID}"

# Crew
CREW = [
    {"name": "Reid Wiseman", "role": "Commander", "agency": "NASA", "social": "@astro_reid"},
    {"name": "Victor Glover", "role": "Pilot", "agency": "NASA", "social": "@VicGlover"},
    {"name": "Christina Koch", "role": "Mission Specialist", "agency": "NASA", "social": "@Astro_Christina"},
    {"name": "Jeremy Hansen", "role": "Mission Specialist", "agency": "CSA", "social": "@Astro_Jeremy"}
]
