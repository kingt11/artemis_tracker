# Artemis II Discord Launch Tracker

## Objective

Build a polling service that monitors the Artemis II mission in real time using The Space Devs Launch Library 2 (LL2) API as the primary data source, augments it with the YouTube Data API v3 to detect the live stream going active, and pushes formatted Discord embeds via webhook to a target channel. The service must cover the full mission arc: pre-launch countdown, launch day, and post-launch mission milestones through splashdown (~10 days).

---

## Live Mission Data (Confirmed via API as of 2026-03-31)

| Field | Value |
|---|---|
| Launch ID | `41699701-2ef4-4b0c-ac9d-6757820cde87` |
| Status | **Go for Launch** (status ID 1) |
| NET (T-0) | `2026-04-01T22:24:00Z` (6:24 PM EDT) |
| Launch Window | 22:24 UTC – 00:24 UTC (2 hours) |
| Weather Probability | **80% GO** |
| Weather Concerns | Cumulus Cloud Rule, Thick Cloud Layers Rule, Ground Winds |
| Pad | Launch Complex 39B, Kennedy Space Center |
| YouTube Broadcast | `https://www.youtube.com/watch?v=Tf_UjBMIzNo` (starts 16:50 UTC / 12:50 PM EDT) |
| NASA+ Broadcast | `https://plus.nasa.gov/scheduled-video/nasas-artemis-ii-crew-launches-to-the-moon-official-broadcast/` |
| Propellant Loading | `2026-04-01T11:45:00Z` |

**Crew:**
- Reid Wiseman — Commander
- Victor Glover — Pilot
- Christina Koch — Mission Specialist
- Jeremy Hansen (CSA) — Mission Specialist

---

## Data Sources & API Analysis

### 1. The Space Devs Launch Library 2 (LL2) — PRIMARY SOURCE

**Base URL:** `https://ll.thespacedevs.com/2.2.0/`

**Key endpoints:**

| Endpoint | Purpose |
|---|---|
| `GET /launch/41699701-2ef4-4b0c-ac9d-6757820cde87/` | Full launch detail: status, NET, probability, vidURLs, webcast_live, timeline |
| `GET /event/upcoming/?search=artemis` | Upcoming mission events (briefings, downlinks, tanking) |

**Fields to monitor on the launch endpoint:**

| Field | Trigger Action |
|---|---|
| `status.id` | Alert on change: 1=Go, 2=TBD, 3=Success, 4=Failure, 5=Hold, 6=In Flight, 7=Partial Failure |
| `net` | Alert when NET shifts (scrub/recycle) |
| `probability` | Alert when weather probability changes |
| `webcast_live` | Alert when flips `true` (stream is live) |
| `vidURLs` | Extract YouTube/NASA+ stream URLs |
| `weather_concerns` | Include in launch-day embeds |
| `holdreason` / `failreason` | Alert on hold with reason |

**Rate limits:** Free tier is ~15 requests/hour. No API key required for public access at this quota. A paid LL2 Launch Library Plus subscription at ~$3/month removes the cap. For launch-day use, a paid key is strongly recommended.

**Timeline data:** The detailed endpoint returns a full `timeline` array with ~80 milestones (each with a relative time offset from T-0 and a description), enabling a computed absolute timestamp for every milestone.

### 2. YouTube Data API v3 — LIVE STREAM DETECTION

**Base URL:** `https://www.googleapis.com/youtube/v3/`

**The official NASA broadcast video ID is already known:** `Tf_UjBMIzNo`

**Key endpoint:**

```
GET /videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo&key=YOUR_API_KEY
```

**Fields to monitor:**

| Field | Trigger Action |
|---|---|
| `snippet.liveBroadcastContent` | `"live"` = stream is active; `"upcoming"` = scheduled; `"none"` = ended |
| `liveStreamingDetails.actualStartTime` | Timestamp when stream actually went live |
| `liveStreamingDetails.concurrentViewers` | Optional: include in embeds as engagement metric |

**Quota cost:** `videos.list` costs 1 quota unit per call (daily quota: 10,000 units free). Polling every 60 seconds for 6 hours = 360 calls — well within quota.

**Fallback discovery:** If NASA publishes a new stream URL on launch day, use `search.list` with `channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video` (100 quota units per call) to auto-discover it.

### 3. NASA Open APIs (`api.nasa.gov`) — LIMITED UTILITY

NASA's public APIs cover science data (APOD, Mars Rover, EONET, etc.) and do **not** expose launch telemetry, orbital position data, or Artemis mission tracking. They are not useful for this use case.

### 4. Artemis Real-Time Orbit Visualization — NOT API-ACCESSIBLE

NASA's Eyes on the Solar System and mission-specific orbit visualizers use WebGL with binary data streams. No public REST endpoint exposes parseable orbital state vectors or trajectory data. This is **not a viable data source** for a webhook pipeline.

### 5. Discord Webhook API

**Endpoint:** `POST https://discord.com/api/webhooks/{webhook_id}/{webhook_token}`

Supports rich embeds with title, description, color, fields, thumbnail, image, timestamp, and footer. No authentication beyond the webhook URL.

---

## Implementation Plan

### Phase 1 — Project Scaffold & Configuration

- [ ] Task 1. **Define configuration schema** — create a config structure (env vars or config file) that stores: LL2 launch ID, LL2 API key (optional), YouTube API key, YouTube video ID, Discord webhook URL, polling intervals per phase, and milestone notification thresholds.

- [ ] Task 2. **Set up project dependencies** — select a runtime (Python with `httpx`/`aiohttp` recommended for async polling, or Node.js with `axios`). Add a scheduler library (`APScheduler` for Python or `node-cron` for Node). Add a Discord embed library or implement raw webhook POST.

- [ ] Task 3. **Implement a simple state store** — use a local JSON file or SQLite to persist the last-known values of `status.id`, `net`, `probability`, `webcast_live`, and `last_modified` so that restarts do not re-fire all alerts.

### Phase 2 — LL2 Poller

- [ ] Task 4. **Implement the LL2 launch detail fetcher** — a function that calls `GET /launch/{id}/` and deserializes the response into a typed data model. Handle HTTP errors and LL2 rate limit responses (HTTP 429) with exponential backoff.

- [ ] Task 5. **Implement change detection** — compare the freshly fetched state against the persisted state and emit typed events for each changed field (`StatusChanged`, `NETShifted`, `ProbabilityChanged`, `WebcastWentLive`, `HoldIssued`).

- [ ] Task 6. **Implement adaptive polling schedule** — define polling intervals based on time-to-launch:
  - `> 24h before NET`: poll every 30 minutes
  - `3h–24h before NET`: poll every 5 minutes
  - `1h–3h before NET`: poll every 2 minutes
  - `< 1h before NET`: poll every 60 seconds
  - `During launch window`: poll every 30 seconds
  - `Post-launch, mission active`: poll every 5 minutes (for event/milestone tracking)

- [ ] Task 7. **Implement timeline milestone extractor** — on first successful fetch, parse the `timeline` array from the launch detail response. Compute each milestone's absolute UTC timestamp by adding its `relative_time` ISO 8601 duration to the confirmed `net`. Store these as scheduled notification triggers.

- [ ] Task 8. **Implement the LL2 events poller** — call `GET /event/upcoming/?search=artemis&limit=10` every 30 minutes to detect new briefings, downlink events, or post-launch news conferences and post them as announcements to the Discord channel.

### Phase 3 — YouTube Live Stream Monitor

- [ ] Task 9. **Implement the YouTube video status poller** — call `GET /videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo` every 60 seconds starting 3 hours before NET. Monitor `liveBroadcastContent` for the transition from `"upcoming"` to `"live"`.

- [ ] Task 10. **Implement live stream discovery fallback** — if the `vidURLs` array in the LL2 response is empty or contains no YouTube entries closer to launch day, fall back to querying the NASA YouTube channel (`channelId=UCLA_DiR1FfKNvjuUpBHmylQ`) with `eventType=live` to auto-discover the active stream URL.

- [ ] Task 11. **Track concurrent viewer count (optional)** — once the stream is live, poll `liveStreamingDetails.concurrentViewers` every 5 minutes and include it in a "mission update" embed.

### Phase 4 — Discord Webhook Notification Engine

- [ ] Task 12. **Define the embed template library** — create distinct embed templates (color-coded by event type) for each notification category:
  - `LAUNCH_COUNTDOWN` (blue): T-24h, T-3h, T-1h, T-30m, T-10m alerts with crew names, NET, weather probability, and live stream link
  - `STATUS_CHANGE` (yellow for hold, green for Go confirmation, red for scrub)
  - `STREAM_LIVE` (bright green): fires when `liveBroadcastContent == "live"`, includes direct YouTube URL and thumbnail
  - `MILESTONE` (purple): timeline events such as propellant loading, hatch close, terminal count, SRB sep, MECO, Orion separation, TLI burn, lunar flyby, splashdown
  - `WEATHER_UPDATE` (orange): fires when probability changes by ≥5%
  - `MISSION_EVENT` (teal): daily briefings, downlink events

- [ ] Task 13. **Implement the webhook POST function** — construct the Discord JSON payload with `embeds` array. Cap embeds at 1 per call to avoid rate limiting. Add a 1-second inter-message delay. Handle Discord rate limit responses (HTTP 429) by honoring the `Retry-After` header.

- [ ] Task 14. **Implement duplicate suppression** — before posting any notification, check the state store to ensure the same event has not already been posted. Use a composite key of `(event_type, field_value, timestamp)`.

### Phase 5 — Countdown Scheduler

- [ ] Task 15. **Schedule fixed pre-launch countdown embeds** — using the confirmed NET of `2026-04-01T22:24:00Z`, pre-schedule embeds at:
  - T-24h: `2026-03-31T22:24:00Z`
  - T-3h: `2026-04-01T19:24:00Z`
  - T-1h: `2026-04-01T21:24:00Z`
  - T-30m: `2026-04-01T21:54:00Z`
  - T-10m: `2026-04-01T22:14:00Z`
  - T-0 (liftoff confirmation via status flip): dynamic
  - If NET shifts due to a hold/recycle, recalculate and reschedule all of these.

- [ ] Task 16. **Schedule key mission milestone notifications** — using the computed absolute timestamps from the `timeline` array, schedule Discord posts for:
  - Propellant loading starts (~T-10h 40m)
  - Flight crew to pad (~T-4h 40m)
  - Hatch closure (~T-3h 40m)
  - Terminal count start (T-10m)
  - Liftoff (T-0)
  - SRB separation (T+2m 8s)
  - MECO (T+8m 6s)
  - Orion solar array deployment (T+20m)
  - Orion/ICPS separation (T+3h 24m)
  - Translunar injection burn (T+~25h)
  - Lunar sphere of influence entry (T+~4d 7h)
  - Lunar closest approach (T+~5d 1h 23m)
  - Max distance from Earth (T+~5d 1h 26m)
  - Orion service module jettison (T+~9d 1h 13m)
  - Splashdown (T+~9d 1h 46m)

### Phase 6 — Resilience & Deployment

- [ ] Task 17. **Implement graceful error handling** — all HTTP calls must catch network errors, non-2xx responses, and JSON parse failures. On error, log the failure, back off, and skip the notification rather than crashing the process.

- [ ] Task 18. **Implement a startup announcement** — on first run, post a "tracker online" embed to the Discord channel confirming it is active, the current launch status, NET, probability, and a direct link to the YouTube stream.

- [ ] Task 19. **Write a process management wrapper** — use `systemd`, `pm2` (Node), or `supervisor` (Python) to run the service as a background process that restarts automatically on crash.

- [ ] Task 20. **Test with a dry-run mode** — implement a `--dry-run` flag that runs all polling and detection logic but replaces the Discord webhook POST with a local console log, allowing full end-to-end verification without spamming the channel.

---

## Verification Criteria

- Polling the LL2 launch endpoint returns HTTP 200 with the correct `id` and `status.abbrev == "Go"` before launch
- A status change from status ID 1 to any other ID fires a Discord embed within the next polling cycle
- The `webcast_live` flag transition from `false` to `true` fires a `STREAM_LIVE` embed containing the confirmed YouTube URL `https://www.youtube.com/watch?v=Tf_UjBMIzNo`
- YouTube API polling correctly identifies `liveBroadcastContent == "live"` as a trigger condition independent of the LL2 flag
- All T-minus countdown embeds fire within 60 seconds of their scheduled time
- No duplicate embeds are posted for the same event
- The service recovers from a 60-second network outage without re-firing past notifications
- At least the following milestones produce Discord notifications: liftoff, MECO, Orion/ICPS separation, TLI burn, lunar flyby, splashdown

---

## Potential Risks and Mitigations

1. **LL2 free tier rate limiting (15 req/hour)** — Polling every 30 seconds during the window exceeds the free tier. Mitigation: Use a Launch Library Plus key ($3/mo), or cache aggressively and only hit the live endpoint every 60 seconds minimum.

2. **Launch scrub or NET shift** — If the launch is scrubbed or recycled, pre-scheduled embeds will fire at the wrong time. Mitigation: The NET change detection in Task 5 cancels and reschedules all downstream jobs whenever `net` changes.

3. **YouTube video ID changes** — NASA could replace the pre-scheduled stream with a different video. Mitigation: The LL2 `vidURLs` array will be updated with the new URL. The poller in Task 4 reads `vidURLs` on every cycle, so the YouTube ID in use is always derived from the latest API response, not hardcoded.

4. **Discord webhook rate limits** — Discord enforces 30 requests per minute per webhook. Mitigation: The inter-message delay in Task 13 and the duplicate suppression in Task 14 ensure the rate is well below this ceiling.

5. **LL2 API downtime** — The Space Devs API has periodic maintenance windows. Mitigation: Cache the last successful response. If the API is unreachable for >10 minutes within the launch window, post a "data source unavailable" warning embed.

6. **`webcast_live` flag lag** — The LL2 community editors update this field manually, so it may lag the actual stream by several minutes. Mitigation: The independent YouTube API poller in Task 9 acts as a parallel detector with no human latency.

---

## Alternative Approaches

1. **Webhooks via LL2 WebSocket (LL2 Plus feature)** — Launch Library Plus provides a WebSocket-based push notification service that eliminates all polling logic and delivers real-time updates the moment the database changes. This is the cleanest architecture but requires a paid subscription and WebSocket connection management.

2. **NASA+ / NASA TV RSS or HLS stream probing** — NASA+ (`plus.nasa.gov`) publishes an HLS manifest for its broadcasts. A service could probe the HLS `.m3u8` URL to detect when the stream goes live without needing a YouTube API key. This works as a YouTube API fallback.

3. **Zapier / Make (no-code automation)** — Third-party automation platforms can monitor the LL2 API via scheduled HTTP request steps and route results to a Discord webhook with no custom code. This trades flexibility and fine-grained control for zero infrastructure overhead.

---

## API Reference Quick Sheet

| API | Endpoint | Auth | Cost |
|---|---|---|---|
| LL2 Launch Detail | `GET https://ll.thespacedevs.com/2.2.0/launch/41699701-2ef4-4b0c-ac9d-6757820cde87/` | None (free) / API key (Plus) | Free: 15 req/hr |
| LL2 Events | `GET https://ll.thespacedevs.com/2.2.0/event/upcoming/?search=artemis` | None | Free: 15 req/hr |
| YouTube Videos | `GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo` | API Key | 1 unit/call, 10k/day free |
| YouTube Search | `GET https://www.googleapis.com/youtube/v3/search?channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video` | API Key | 100 units/call |
| Discord Webhook | `POST https://discord.com/api/webhooks/{id}/{token}` | Webhook URL | Free |
