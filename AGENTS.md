# AGENTS.md — Artemis II Discord Launch Tracker

## Project Overview

A polling service that monitors the Artemis II mission in real time and pushes formatted Discord embeds via webhook across three dedicated channels. Built against The Space Devs Launch Library 2 (LL2) API v2.3.0 as the primary source, augmented by the YouTube Data API v3 and Spaceflight News API (SNAPI). Coverage spans the full mission arc from pre-launch through Pacific Ocean splashdown (~10 days, ~April 1–11, 2026).

**Primary plan document:** `plans/2026-03-31-artemis-ii-discord-tracker-v3.md` — treat this as the implementation spec.

---

## Mission-Critical Constants (Hardcoded Seed Values)

These values are confirmed from live API data and used to bootstrap the service before the first poll returns.

| Constant | Value |
|---|---|
| LL2 Launch ID | `41699701-2ef4-4b0c-ac9d-6757820cde87` |
| NET (T-0) | `2026-04-01T22:24:00Z` |
| YouTube Video ID | `Tf_UjBMIzNo` |
| YouTube Full URL | `https://www.youtube.com/watch?v=Tf_UjBMIzNo` |
| NASA+ Stream URL | `https://plus.nasa.gov/scheduled-video/nasas-artemis-ii-crew-launches-to-the-moon-official-broadcast/` |
| Mission Patch URL | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/mission_patch_images/artemis2520ii_mission_patch_20250404074145.png` |
| Launch Thumbnail URL | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/images/255bauto255d__image_thumbnail_20240305193913.jpeg` |
| Infographic URL | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/infographic_images/sls2520block2_infographic_20260329082241.jpeg` |
| FlightClub Trajectory | `https://flightclub.io/result?llId=41699701-2ef4-4b0c-ac9d-6757820cde87` |
| NASA YouTube Channel ID | `UCLA_DiR1FfKNvjuUpBHmylQ` |
| Expected splashdown MET | T+9d 1h 46m (~April 11) |

---

## Crew

| Name | Role | Agency | X/Twitter handle |
|---|---|---|---|
| Reid Wiseman | Commander | NASA | `@astro_reid` |
| Victor Glover | Pilot | NASA | `@VicGlover` |
| Christina Koch | Mission Specialist | NASA | `@Astro_Christina` |
| Jeremy Hansen | Mission Specialist | CSA | `@Astro_Jeremy` |

In LL2 v2.3.0, social handles are under `astronaut.social_media_links[{social_media.name, url}]` — iterate the array and match on `social_media.name`.

---

## Data Sources

### 1. The Space Devs Launch Library 2 (LL2) v2.3.0

**Base URL:** `https://ll.thespacedevs.com/2.3.0/`  
**Auth:** None. **Rate limit: 15 req/hour (free tier).** Never exceed this.

| Endpoint | Purpose |
|---|---|
| `GET /launches/{id}/` | Launch detail: status, NET, probability, vidURLs, timeline, crew, updates |
| `GET /events/upcoming/?search=artemis&limit=10` | Upcoming briefings, downlinks, press conferences |

**Fields to monitor on launch detail:**

| Field | JSON path (v2.3.0) | Action on change |
|---|---|---|
| Status | `status.id` | Emit `StatusChanged` |
| NET | `net` | Emit `NETShifted`, recompute all milestone timestamps |
| Weather probability | `probability` | Emit `ProbabilityChanged` |
| Weather concerns | `weather_concerns` | Include in `WEATHER_UPDATE` embed |
| Webcast live flag | `webcast_live` | Emit `WebcastWentLive` |
| YouTube stream URL | `vidURLs[].url` where hostname contains `youtube.com` | Extract dynamically |
| Hold reason | `holdreason` | Include in `HOLD_UPDATE` embed |
| Fail reason | `failreason` | Include in `STATUS_CHANGE` (scrub) embed |
| LL2 update entries | `updates[].id` | Emit `NewUpdateEntry` for any id > stored max |

**v2.3.0 breaking schema differences vs. v2.2.0:**

| What | v2.2.0 | v2.3.0 |
|---|---|---|
| All endpoints | Singular (`/launch/`, `/event/`) | **Plural** (`/launches/`, `/events/`) — 404 on singular |
| Image URL | `launch.image` (bare string) | `launch.image.image_url` (object) |
| Thumbnail | Did not exist | `launch.image.thumbnail_url` (new — use for Discord embed thumbnails) |
| Crew socials | `astronaut.twitter`, `.instagram` (flat) | `astronaut.social_media_links[{social_media.name, url}]` (array) |
| Spacecraft stage | `spacecraft_stage` (object) | `spacecraft_stage[]` (array — always access `[0]`) |
| Splashdown location | `landing.location` | `landing.landing_location` |
| Pad lat/lon | Strings | Numbers |
| Event video live indicator | Did not exist | `vid_urls[].live` (boolean per video) |

### 2. YouTube Data API v3

**Endpoint:** `GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo&key=YOUR_KEY`  
**Auth:** API key (env var `YOUTUBE_API_KEY`).  
**Quota:** 1 unit/call, 10,000/day free. Start polling 3 hours before NET, every 60 seconds.

| Field | Trigger |
|---|---|
| `snippet.liveBroadcastContent == "live"` | Fire `STREAM_LIVE` embed (independent of LL2) |
| `liveStreamingDetails.concurrentViewers` | Append to periodic mission embeds once live |

**Fallback:** If LL2 `vidURLs` has no YouTube entry, query `search.list?channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video` (100 units/call — use sparingly).

### 3. Spaceflight News API (SNAPI)

**Endpoint:** `GET https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&limit=5&ordering=-published_at`  
**Auth:** None. **Rate limit:** None documented.  
**Poll:** Every 30 minutes, independent of the 15 req/hr LL2 budget.  
**Dedup:** Track `last_seen_snapi_id` in state store. Post only articles where `id > last_seen_snapi_id`.

### 4. Discord Webhook API

**New message:** `POST https://discord.com/api/webhooks/{id}/{token}`  
**Edit existing:** `PATCH https://discord.com/api/webhooks/{id}/{token}/messages/{message_id}`  
**Rate limit:** 30 req/min per webhook. Enforce 1-second delay between sequential posts to the same webhook.

---

## Channel Architecture

Three channels → three webhook URLs, stored in env vars.

```
DISCORD_WEBHOOK_ALERTS     →  #artemis-alerts
DISCORD_WEBHOOK_MISSION    →  #artemis-mission
DISCORD_WEBHOOK_NEWS       →  #artemis-news
```

### Routing Table

| Embed Type | Channel | Role Ping? |
|---|---|---|
| `TRACKER_ONLINE` | `#artemis-alerts` | No |
| `CREW_INTRO` | `#artemis-mission` | No |
| `LAUNCH_COUNTDOWN` | `#artemis-mission` | No |
| `STATUS_CHANGE` | `#artemis-alerts` | **Yes** |
| `HOLD_UPDATE` | `#artemis-alerts` | **Yes (initial POST only)** |
| `NET_SHIFT` | `#artemis-alerts` | **Yes** |
| `WEATHER_UPDATE` | `#artemis-mission` | No |
| `STREAM_LIVE` | `#artemis-alerts` | **Yes** |
| `MILESTONE` | `#artemis-mission` | No |
| `HISTORICAL_MILESTONE` | `#artemis-mission` | No |
| `MISSION_DAY` | `#artemis-mission` | No |
| `MISSION_EVENT` | `#artemis-news` | No |
| `NEWS` | `#artemis-news` | No |
| `SPLASHDOWN` | `#artemis-alerts` | **Yes** |

**Ping implementation:** Include `<@&ROLE_ID>` in the `content` field (not inside the embed object) for pinging embeds. On hold duration edits (PATCH), do not re-ping — the role ID was already in the original POST.

**Hold duration editing pattern:** On `HoldIssued`, POST the initial `HOLD_UPDATE` embed, store the returned Discord `message_id` in the state store. Every 15 minutes, PATCH that message ID with updated hold duration. On `HoldLifted`, POST a new `STATUS_CHANGE` (green) and clear the stored message ID.

---

## Polling Schedule (≤ 15 req/hour — do not exceed)

| Phase | Window | Interval | Req/hr |
|---|---|---|---|
| Distant pre-launch | > 24h before NET | 30 min | 2 |
| Near pre-launch | 3h – 24h before NET | 10 min | 6 |
| Final approach | 1h – 3h before NET | 8 min | ~7 |
| Launch window | < 1h before NET → window close | 4 min | **15 (max)** |
| Mission active | Liftoff → splashdown confirmed | 15 min | 4 |
| Wind-down | After splashdown | 30 min | 2 |

LL2 events poll and SNAPI poll each run on a fixed 30-minute interval, counted separately from the main launch detail poll.

---

## State Store Schema

Persist to JSON file or SQLite. Must survive process restarts.

```
{
  "last_status_id": int,
  "last_net": "ISO8601 string",
  "last_probability": int,
  "last_webcast_live": bool,
  "last_ll2_update_id": int,
  "last_snapi_article_id": int,
  "hold_start_utc": "ISO8601 string or null",
  "hold_discord_message_id": "string or null",
  "fired_notifications": ["composite_key_1", "composite_key_2", ...],
  "milestone_schedule": [
    {"name": string, "absolute_utc": "ISO8601", "embed_type": string, "fired": bool}
  ]
}
```

Composite key format for `fired_notifications`: `"{embed_type}:{discriminator}"` (e.g., `"STATUS_CHANGE:1"`, `"MILESTONE:sls_liftoff"`, `"NEWS:7821"`).

---

## Historical Milestone Triggers

These three are `HISTORICAL_MILESTONE` type (gold color) with special contextual copy:

| Event | MET offset | Context copy |
|---|---|---|
| TLI burn | +1d 1h 37m | "First humans to leave Earth orbit since Apollo 17, December 1972 — 53+ years" |
| Lunar flyby | +4d 22h | "First humans near the Moon since 1972; first Canadian to enter lunar space (Jeremy Hansen)" |
| Lunar closest approach | +5d 1h 23m | Include closest approach distance (from LL2 timeline if available) |
| Max distance from Earth | +5d 1h 26m | "Humans at maximum distance from Earth on this mission" |

---

## Embed Color Codes

| Embed Type | Hex Color |
|---|---|
| `TRACKER_ONLINE` | `#808080` (grey) |
| `CREW_INTRO` | `#003087` (deep blue) |
| `LAUNCH_COUNTDOWN` | `#1E6BE6` (blue) |
| `STATUS_CHANGE` hold | `#FFD700` (yellow) |
| `STATUS_CHANGE` go-confirm | `#00CC44` (green) |
| `STATUS_CHANGE` scrub | `#FF2200` (red) |
| `HOLD_UPDATE` | `#FF8C00` (orange) |
| `NET_SHIFT` | `#FF4500` (red-orange) |
| `STREAM_LIVE` | `#00FF88` (bright green) |
| `WEATHER_UPDATE` | `#FF8C00` (orange) |
| `MILESTONE` | `#7B2FBE` (purple) |
| `HISTORICAL_MILESTONE` | `#FFB300` (gold) |
| `MISSION_DAY` | `#3F51B5` (indigo) |
| `MISSION_EVENT` | `#008B8B` (teal) |
| `NEWS` | `#606060` (grey) |
| `SPLASHDOWN` | `#00CC44` (green) |

---

## Environment Variables

```
LL2_LAUNCH_ID                     # = 41699701-2ef4-4b0c-ac9d-6757820cde87
YOUTUBE_API_KEY                   # Google Cloud credentials
YOUTUBE_VIDEO_ID                  # = Tf_UjBMIzNo
DISCORD_WEBHOOK_ALERTS
DISCORD_WEBHOOK_MISSION
DISCORD_WEBHOOK_NEWS
DISCORD_ROLE_ID                   # Role ID to ping (moderate setting)
STATE_FILE_PATH                   # Path to JSON/SQLite state store
DRY_RUN                           # "true" = console output only, no Discord posts
```

---

## Recommended Tech Stack

- **Python 3.11+** with `httpx` (async HTTP), `APScheduler` (job scheduling), and `sqlite3` or a flat JSON state file.
- **Node.js 20+** with `axios` and `node-cron` as a viable alternative.

The service runs as a long-lived background process. Use `systemd`, `pm2` (Node), or `supervisor` (Python) for process management with auto-restart.

---

## Key Implementation Rules

1. **Never exceed 15 LL2 requests per hour.** The polling phases are calculated to stay at or below this. The SNAPI and LL2 events polls are separate counters.
2. **All milestone timestamps are relative to `net`.** Any `NETShifted` event must cancel all pending milestone jobs and recompute from the new `net` value before rescheduling.
3. **Duplicate suppression is mandatory.** Before posting any embed, check `fired_notifications` in the state store for the composite key. This must survive restarts.
4. **Image assets:** Use `launch.image.thumbnail_url` for Discord embed `thumbnail.url` and `launch.image.image_url` for full-size `image.url`. Do not use the v2.2.0 bare `launch.image` string.
5. **MET footer:** Every embed posted after liftoff includes a "Mission Elapsed Time: Xd Xh Xm" footer field.
6. **`--dry-run` mode** must replace all webhook POSTs and PATCHes with structured console output. All polling and detection logic still runs against live APIs.

---

## File Structure (Suggested)

```
artemis/
├── AGENTS.md                          ← This file
├── plans/
│   └── 2026-03-31-artemis-ii-discord-tracker-v3.md   ← Full implementation spec
├── src/
│   ├── config.py / config.js          ← Env var loading, constants
│   ├── state.py / state.js            ← State store read/write
│   ├── poller_ll2.py / poller_ll2.js  ← LL2 launch + events polling + change detection
│   ├── poller_youtube.py              ← YouTube live detection + viewer count
│   ├── poller_snapi.py                ← Spaceflight news fetcher
│   ├── scheduler.py / scheduler.js   ← Adaptive polling + milestone job scheduling
│   ├── embeds.py / embeds.js          ← All embed constructors, color codes
│   ├── webhook.py / webhook.js        ← Discord POST/PATCH router with rate limit delay
│   └── main.py / main.js             ← Entry point, initializes all pollers and scheduler
├── state.json                         ← Runtime state (gitignore)
└── .env                               ← Secrets (gitignore)
```
