# Artemis II Discord Launch Tracker

## Objective

Build a polling service that monitors the Artemis II mission in real time using The Space Devs Launch Library 2 (LL2) API v2.3.0 as the primary data source, augments it with the YouTube Data API v3 for live-stream detection and the Spaceflight News API (SNAPI) for coverage articles, and pushes formatted Discord embeds via webhook to three dedicated channels. The service covers the full mission arc from pre-launch countdown through Pacific Ocean splashdown (~10 days, April 1–11, 2026).

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
| YouTube Broadcast | `https://www.youtube.com/watch?v=Tf_UjBMIzNo` (starts 16:50 UTC) |
| YouTube Video ID | `Tf_UjBMIzNo` |
| NASA+ Broadcast | `https://plus.nasa.gov/scheduled-video/nasas-artemis-ii-crew-launches-to-the-moon-official-broadcast/` |
| Mission Patch URL | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/mission_patch_images/artemis2520ii_mission_patch_20250404074145.png` |
| Launch Thumbnail URL | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/images/255bauto255d__image_thumbnail_20240305193913.jpeg` |
| Infographic URL | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/infographic_images/sls2520block2_infographic_20260329082241.jpeg` |
| FlightClub Trajectory | `https://flightclub.io/result?llId=41699701-2ef4-4b0c-ac9d-6757820cde87` |
| Splashdown | Pacific Ocean, ~T+9d 1h 46m (~April 11) |

**Crew (all data available in LL2 API v2.3.0):**
| Name | Role | Agency | Social |
|---|---|---|---|
| Reid Wiseman | Commander | NASA | @astro_reid (X) |
| Victor Glover | Pilot | NASA | @VicGlover (X) |
| Christina Koch | Mission Specialist | NASA | @Astro_Christina (X/Instagram) |
| Jeremy Hansen | Mission Specialist | CSA | @Astro_Jeremy (X) |

**Notable firsts:**
- First crewed Artemis mission
- First humans beyond low Earth orbit since Apollo 17 (December 1972 — 53+ years)
- First Canadian to leave Earth orbit

---

## Data Sources & API Reference

### 1. The Space Devs Launch Library 2 (LL2) v2.3.0 — PRIMARY SOURCE

**Base URL:** `https://ll.thespacedevs.com/2.3.0/`  
**Auth:** None required (free tier: 15 req/hour)

> **v2.3.0 note:** All resource endpoints are plural (e.g., `/launches/`, `/events/`, `/astronauts/`). The singular forms used in v2.2.0 return 404. See schema changes section below.

| Endpoint | Purpose |
|---|---|
| `GET /launches/41699701-2ef4-4b0c-ac9d-6757820cde87/` | Full launch detail: status, NET, probability, vidURLs, timeline, crew, patches, infographic |
| `GET /events/upcoming/?search=artemis&limit=10` | Upcoming mission events: briefings, downlinks, news conferences |

**Fields monitored on the launch endpoint:**

| Field | Path in v2.3.0 | Trigger |
|---|---|---|
| Status | `status.id` | Alert on any change |
| NET | `net` | Alert when value shifts (scrub/recycle) |
| Weather probability | `probability` | Alert when value changes |
| Weather concerns | `weather_concerns` | Include in weather update embeds |
| Webcast live flag | `webcast_live` | Alert when flips `true` |
| Video URLs | `vidURLs[].url` where `source == "youtube.com"` | Extract YouTube stream URL dynamically |
| Hold reason | `holdreason` | Include in hold embeds |
| Fail reason | `failreason` | Include in scrub embeds |
| LL2 update entries | `updates[].id` | Monitor for new entries (forecasts, editor notes) |

**v2.3.0 schema changes vs. v2.2.0 (breaking):**

| Field | v2.2.0 | v2.3.0 |
|---|---|---|
| Launch image URL | `launch.image` (bare string) | `launch.image.image_url` (object) |
| Launch thumbnail | *(did not exist)* | `launch.image.thumbnail_url` (new) |
| Crew social links | `astronaut.twitter`, `astronaut.instagram` (flat strings) | `astronaut.social_media_links[{social_media.name, url}]` (structured array) |
| Spacecraft stage | `spacecraft_stage` (object) | `spacecraft_stage[]` (array — access as `[0]`) |
| Splashdown location | `landing.location` | `landing.landing_location` |
| Pad lat/lon | Strings | Numbers |
| Event stream live indicator | *(not present)* | `vid_urls[].live` boolean per video entry |

### 2. YouTube Data API v3 — LIVE STREAM DETECTION

**Endpoint:** `GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo&key=YOUR_KEY`

| Field | Trigger |
|---|---|
| `snippet.liveBroadcastContent` | `"live"` fires STREAM_LIVE embed |
| `liveStreamingDetails.actualStartTime` | Confirms stream start timestamp |
| `liveStreamingDetails.concurrentViewers` | Included in periodic mission status embeds |

**Quota:** 1 unit/call, 10,000/day free. Polling every 60 seconds for 6 hours = 360 units.

**Fallback discovery:** If `vidURLs` in the LL2 response contains no YouTube entry, query `search.list` on NASA's channel (`channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video`) to auto-discover the active stream.

### 3. Spaceflight News API (SNAPI) — NEWS FEED

**Endpoint:** `GET https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&limit=5&ordering=-published_at`  
**Auth:** None. Free. No documented rate limit.

Returns articles from major outlets (NASASpaceFlight.com, Spaceflight Now, SpaceNews, Ars Technica). Key fields: `id`, `title`, `newsSite`, `summary`, `url`, `imageUrl`, `publishedAt`.

Poll every 30 minutes. Track the highest-seen `id` in the state store. Post any article with `id > last_seen_id` as a `NEWS` embed.

### 4. Discord Webhook API

**New message:** `POST https://discord.com/api/webhooks/{id}/{token}`  
**Edit existing message:** `PATCH https://discord.com/api/webhooks/{id}/{token}/messages/{message_id}`  
Rate limit: 30 req/minute per webhook. Use a 1-second delay between sequential posts to the same webhook.

---

## Discord Channel Architecture

Three channels, three webhooks, content routed by urgency and signal type.

```
#artemis-alerts      Webhook A    ← Highest signal. Notifications ON. Role pings here.
#artemis-mission     Webhook B    ← Mission tracking. Notifications optional.
#artemis-news        Webhook C    ← Informational. Can be muted.
```

### Channel Routing Table

| Embed Type | Target Channel | Role Ping? |
|---|---|---|
| `TRACKER_ONLINE` — startup confirmation | `#artemis-alerts` | No |
| `CREW_INTRO` — crew bios, roles, social links | `#artemis-mission` | No |
| `LAUNCH_COUNTDOWN` — T-24h, T-3h, T-1h, T-30m, T-10m | `#artemis-mission` | No |
| `STATUS_CHANGE` — any `status.id` transition | `#artemis-alerts` | **Yes** |
| `HOLD_UPDATE` — hold active + duration edits | `#artemis-alerts` | **Yes** (initial post only) |
| `NET_SHIFT` — NET changes (scrub/recycle/delay) | `#artemis-alerts` | **Yes** |
| `WEATHER_UPDATE` — probability change or new forecast PDF | `#artemis-mission` | No |
| `STREAM_LIVE` — YouTube `"live"` or LL2 `webcast_live` flip | `#artemis-alerts` | **Yes** |
| `MILESTONE` — countdown and post-launch timeline events | `#artemis-mission` | No |
| `HISTORICAL_MILESTONE` — first humans beyond LEO since 1972, etc. | `#artemis-mission` | No |
| `MISSION_DAY` — daily mission day summary | `#artemis-mission` | No |
| `MISSION_EVENT` — LL2 briefings, downlinks, conferences | `#artemis-news` | No |
| `NEWS` — SNAPI articles | `#artemis-news` | No |
| `SPLASHDOWN` — mission complete | `#artemis-alerts` | **Yes** |

**Role ping implementation:** For embeds with "Yes" in the ping column, include `<@&ROLE_ID>` in the `content` field of the Discord webhook payload (outside the embed object itself). For hold updates that edit the original message via PATCH, the ping fires only on the initial POST; subsequent edits do not re-ping.

**Summary of role-pinged events:**
- Any `status.id` change (Go → Hold, Hold → Go, any → Scrub/Success/Failure)
- NET shift (T-0 moves for any reason)
- Stream going live
- Splashdown confirmed

---

## Polling Schedule (≤ 15 req/hour, LL2 only)

| Phase | Window | Interval | Req/hr |
|---|---|---|---|
| Distant pre-launch | > 24h before NET | Every 30 min | 2 |
| Near pre-launch | 3h – 24h before NET | Every 10 min | 6 |
| Final approach | 1h – 3h before NET | Every 8 min | ~7 |
| Launch window | < 1h before NET through window close | Every 4 min | 15 (at limit) |
| Post-launch, mission active | Liftoff through splashdown | Every 15 min | 4 |
| Mission complete | After splashdown confirmed | Every 30 min (wind-down) | 2 |

SNAPI and LL2 events polls each run on an independent fixed 30-minute interval, counted separately from the main launch detail poll.

---

## Implementation Plan

### Phase 1 — Project Scaffold & Configuration

- [ ] Task 1. **Define configuration schema** — store in env vars or a config file: LL2 launch ID, YouTube API key, YouTube video ID (`Tf_UjBMIzNo`), three Discord webhook URLs (one per channel), Discord role ID for moderate pings, polling intervals per phase, and milestone notification opt-in flags.

- [ ] Task 2. **Set up project dependencies** — select a runtime (Python with `httpx` + `APScheduler` recommended, or Node.js with `axios` + `node-cron`). Add an HTTP client, a scheduler, and a JSON-based or SQLite state store library.

- [ ] Task 3. **Implement a persistent state store** — persist: last-known `status.id`, `net`, `probability`, `webcast_live`, the ID of the last-seen SNAPI article, the last-seen LL2 update entry ID, stored Discord message IDs for editable embeds (hold updates), and a log of all previously fired notification composite keys (for duplicate suppression).

- [ ] Task 4. **Implement the webhook router** — a single dispatch function that accepts an embed payload plus an `embed_type` parameter and routes to the correct webhook URL based on the channel routing table. Handles POST for new messages and PATCH for message edits. Enforces the 1-second inter-message delay.

### Phase 2 — LL2 Poller

- [ ] Task 5. **Implement the LL2 launch detail fetcher** — call `GET https://ll.thespacedevs.com/2.3.0/launches/{id}/` and deserialize using the v2.3.0 schema (plural endpoints, image objects, `spacecraft_stage[0]`, `landing.landing_location`, structured `social_media_links`). On HTTP 429, back off for the `Retry-After` duration and skip that cycle.

- [ ] Task 6. **Implement change detection** — compare freshly fetched state against the state store and emit typed internal events: `StatusChanged`, `NETShifted`, `ProbabilityChanged`, `WebcastWentLive`, `HoldIssued`, `HoldLifted`, `NewUpdateEntry`.

- [ ] Task 7. **Implement adaptive polling scheduler** — schedule the LL2 fetch at the intervals from the polling table. Recalculate which phase applies on each tick using `now` vs. the stored `net`. When `net` changes, recalculate phase and reschedule immediately.

- [ ] Task 8. **Implement timeline milestone extractor** — on first successful fetch, parse the `timeline` array. Compute each milestone's absolute UTC timestamp by adding its ISO 8601 `relative_time` offset to the confirmed `net`. Store as a sorted trigger list. Recompute all timestamps if `net` changes.

- [ ] Task 9. **Implement the LL2 events poller** — call `GET https://ll.thespacedevs.com/2.3.0/events/upcoming/?search=artemis&limit=10` every 30 minutes. Compare returned event IDs against state. Post new events as `MISSION_EVENT` embeds to `#artemis-news`. Note: v2.3.0 adds a `vid_urls[].live` boolean per video entry on events — use this to detect when an event's stream goes live independently.

- [ ] Task 10. **Implement 45th Weather Squadron update monitor** — on each LL2 launch fetch, check `updates[]` for entries with `id` greater than the stored last-seen value. When a new entry's `info_url` matches the 45th Weather Squadron domain, post a `WEATHER_UPDATE` embed to `#artemis-mission` with the forecast PDF link.

### Phase 3 — YouTube Live Stream Monitor

- [ ] Task 11. **Implement the YouTube video status poller** — call `GET /videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo` every 60 seconds starting 3 hours before NET. Detect `liveBroadcastContent == "live"` independently of the LL2 `webcast_live` flag. Whichever source detects live first wins; the duplicate suppressor prevents double-posting.

- [ ] Task 12. **Implement live stream discovery fallback** — if LL2 `vidURLs` contains no YouTube entry, query `search.list` on `channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video` to auto-discover the stream.

- [ ] Task 13. **Implement concurrent viewer tracking** — once live, poll `liveStreamingDetails.concurrentViewers` every 10 minutes and append the figure as a field in the next `MILESTONE` embed posted to `#artemis-mission`.

### Phase 4 — Spaceflight News API Poller

- [ ] Task 14. **Implement the SNAPI news fetcher** — call `GET /v4/articles/?search=Artemis+II&limit=5&ordering=-published_at` every 30 minutes. Filter for `id > last_seen_id`. Post each new article as a `NEWS` embed to `#artemis-news` with title, source site, summary, thumbnail, and direct link.

### Phase 5 — Discord Notification Engine

- [ ] Task 15. **Define embed template library** — implement color-coded embed constructors per type:
  - `TRACKER_ONLINE` (grey) → `#artemis-alerts`: online confirmation, current status, NET, stream link
  - `CREW_INTRO` (deep blue) → `#artemis-mission`: mission patch thumbnail, full crew roster with bios, roles, social handles, FlightClub link, mission infographic as embed image
  - `LAUNCH_COUNTDOWN` (blue) → `#artemis-mission`: T-minus label, NET in multiple timezones, weather %, stream links, mission patch thumbnail
  - `STATUS_CHANGE` (yellow=hold, green=go-confirmed, red=scrub) → `#artemis-alerts`: new status name, description, holdreason/failreason if populated — **role ping**
  - `HOLD_UPDATE` (orange) → `#artemis-alerts`: hold duration (edited in-place via PATCH), estimated resume time if known — **role ping on initial POST only**
  - `NET_SHIFT` (red-orange) → `#artemis-alerts`: old NET, new NET, delta — **role ping**
  - `STREAM_LIVE` (bright green) → `#artemis-alerts`: YouTube link, stream thumbnail, NASA+ link, note on concurrent viewers — **role ping**
  - `WEATHER_UPDATE` (orange) → `#artemis-mission`: new probability %, weather concerns, forecast PDF link if available
  - `MILESTONE` (purple) → `#artemis-mission`: milestone name, MET footer post-liftoff, next milestone preview
  - `HISTORICAL_MILESTONE` (gold) → `#artemis-mission`: milestone name, historical context text (first humans beyond LEO since 1972, first Canadian beyond LEO), mission patch thumbnail
  - `MISSION_DAY` (indigo) → `#artemis-mission`: day number, MET, current phase, next 2–3 activities from the timeline
  - `MISSION_EVENT` (teal) → `#artemis-news`: event name, date/time, description, YouTube link if in `vid_urls`
  - `NEWS` (grey) → `#artemis-news`: headline, source, summary, thumbnail, link
  - `SPLASHDOWN` (green) → `#artemis-alerts`: total mission duration, Pacific Ocean recovery location with Google Maps link, crew names — **role ping**

- [ ] Task 16. **Implement duplicate suppression** — before posting, check the state store for composite key `(embed_type, field_value, utc_minute_bucket)`. Skip if found. This prevents re-fires after restarts.

- [ ] Task 17. **Implement hold duration tracker** — when `StatusChanged` emits with `new_status == 5`, record hold start time and store the Discord message ID of the initial `HOLD_UPDATE` post. Every 15 minutes, PATCH that message to update "Hold duration: Xh Xm". When `HoldLifted` emits, post a new `STATUS_CHANGE` (green) embed and stop the hold timer. Recompute all milestone timestamps against the new `net`.

### Phase 6 — Countdown & Mission Scheduler

- [ ] Task 18. **Schedule fixed pre-launch countdown embeds** — using confirmed NET `2026-04-01T22:24:00Z`:
  - T-24h: `CREW_INTRO` then `LAUNCH_COUNTDOWN` pair to `#artemis-mission`
  - T-3h: `LAUNCH_COUNTDOWN` with current weather probability
  - T-1h: `LAUNCH_COUNTDOWN` with stream link prominent
  - T-30m: `LAUNCH_COUNTDOWN`
  - T-10m: `LAUNCH_COUNTDOWN` with liftoff-imminent language
  - All reschedule automatically if `net` changes.

- [ ] Task 19. **Schedule key launch-phase milestone embeds** — computed from `timeline` array:
  - Propellant loading GO (T-10h 50m)
  - Flight crew to pad (T-4h 40m)
  - Crew boarding Orion (T-4h)
  - Hatch closure (T-3h 40m)
  - Terminal count start (T-10m)
  - Liftoff / SRB ignition (T-0)
  - Max-Q (T+1m 10s)
  - SRB separation (T+2m 8s)
  - MECO (T+8m 6s)
  - Orion solar array deployment (T+20m)
  - Orion/ICPS separation (T+3h 24m)

- [ ] Task 20. **Schedule trans-lunar and mission milestone embeds** — key post-launch events with `MILESTONE` or `HISTORICAL_MILESTONE` type:
  - TLI burn (MET +1d 1h 37m): `HISTORICAL_MILESTONE` — "First humans leaving Earth orbit since Apollo 17, December 1972"
  - Orion enters lunar sphere of influence (MET +4d 7h): `MILESTONE`
  - Lunar flyby begins (MET +4d 22h): `HISTORICAL_MILESTONE` — "First humans near the Moon since 1972; first Canadian to enter lunar space"
  - Lunar closest approach (MET +5d 1h 23m): `HISTORICAL_MILESTONE` — closest approach distance note
  - Max distance from Earth (MET +5d 1h 26m): `HISTORICAL_MILESTONE` — "Humans at maximum distance from Earth on this mission"
  - Orion exits lunar sphere of influence (MET +5d 19h 47m): `MILESTONE`
  - Crew entry preparations (MET +8d 22h 30m): `MILESTONE`
  - Atmospheric entry (MET +9d 1h 33m): `MILESTONE`
  - Splashdown (MET +9d 1h 46m): `SPLASHDOWN` — role ping, Pacific Ocean Google Maps link

- [ ] Task 21. **Schedule daily Mission Day embeds** — post once per day at 14:00 UTC starting Mission Day 2 (April 3) through splashdown day. Each `MISSION_DAY` embed includes day number, current mission phase, MET, and the next 2–3 notable activities from the timeline for that day.

### Phase 7 — Resilience & Local Testing

- [ ] Task 22. **Implement graceful error handling** — all HTTP calls catch network errors, non-2xx responses, and JSON parse failures. On LL2 unavailability during the launch window, post a single `STATUS_CHANGE`-style warning to `#artemis-alerts` and resume silently once connectivity returns. The timeline milestone scheduler continues firing from the cached schedule regardless.

- [ ] Task 23. **Write a process management wrapper** — use `systemd`, `pm2` (Node), or `supervisor` (Python) to run the service as a background process with automatic restart on crash. The unit/config file should be committed to the repository so it can be installed on the Linode server directly from the clone.

- [ ] Task 24. **Implement `--dry-run` mode** — replaces all Discord webhook POSTs/PATCHes with structured console output. Runs full polling and detection logic against live APIs for end-to-end pipeline verification without posting to any channel. Run this locally before every deployment to confirm the pipeline is healthy.

### Phase 8 — GitHub Repository & Linode Deployment

- [ ] Task 25. **Initialize the Git repository and configure `.gitignore`** — initialize a Git repo at the project root if one does not exist. The `.gitignore` must exclude: `.env`, `state.json` (or `state.db`), `__pycache__/`, `*.pyc`, `node_modules/`, and any editor-specific directories. Secrets must never be committed.

- [ ] Task 26. **Create a `.env.example` file** — commit a `.env.example` that lists every required environment variable with placeholder values and inline comments describing each one. This serves as the setup reference when configuring the server. Never commit the real `.env`.

- [ ] Task 27. **Push the project to a GitHub repository** — create a new repository on GitHub (recommended: private, given the `.env.example` contains the variable names for webhook URLs and API keys). Push all committed source files, the `AGENTS.md`, the `plans/` directory, the `.env.example`, the process manager config file (systemd unit or pm2 ecosystem file), and a `requirements.txt` or `package.json`.

- [ ] Task 28. **Provision the Linode server runtime** — SSH into the Linode instance and install the required runtime. For Python: install `python3`, `pip`, and `python3-venv` via the system package manager. For Node.js: install via `nvm` or the NodeSource apt repository. Confirm the installed version matches the minimum required by the project.

- [ ] Task 29. **Clone the repository onto the Linode server** — run `git clone <repo-url>` in the desired working directory (e.g., `/opt/artemis-tracker` or `~/artemis-tracker`). Install dependencies: `pip install -r requirements.txt` inside a virtualenv (Python) or `npm install` (Node.js).

- [ ] Task 30. **Configure the production `.env` on the Linode server** — copy `.env.example` to `.env` in the cloned directory and populate all values: the three Discord webhook URLs, the Discord role ID, the YouTube API key, the LL2 launch ID, and the state file path. Set restrictive file permissions (`chmod 600 .env`) so the secrets are not world-readable.

- [ ] Task 31. **Run `--dry-run` on the Linode server before going live** — execute the service in dry-run mode from the server to confirm all API connections are reachable, environment variables are loaded correctly, and the embed pipeline produces expected console output. Resolve any import, dependency, or network errors before enabling live webhook posting.

- [ ] Task 32. **Install and enable the process manager on the Linode server** — install and configure the committed `systemd` unit file (or `pm2` ecosystem file / `supervisor` config) so the tracker runs as a managed background service. Enable it to start automatically on server reboot. Start the service and confirm the `TRACKER_ONLINE` embed appears in `#artemis-alerts`.

- [ ] Task 33. **Establish a git-pull update workflow** — on the Linode server, updates are deployed by running `git pull` in the project directory followed by a service restart. Document this two-command sequence in a comment in the process manager config file so it is self-evident to anyone SSHing into the server later.

---

## Verification Criteria

- All three webhooks receive the correct embed types per the channel routing table
- Role pings appear in `#artemis-alerts` for: status change, NET shift, stream live, splashdown — and not in `#artemis-mission` or `#artemis-news`
- A hold event fires a `HOLD_UPDATE` to `#artemis-alerts` with a ping, then edits that message silently every 15 minutes
- YouTube `liveBroadcastContent == "live"` triggers `STREAM_LIVE` to `#artemis-alerts` independently of LL2 `webcast_live`
- `CREW_INTRO` posts to `#artemis-mission` (not `#artemis-alerts`) at T-24h
- New SNAPI articles appear in `#artemis-news` within 30 minutes of publication
- `HISTORICAL_MILESTONE` embeds fire at TLI burn, lunar flyby, lunar closest approach, and max distance
- Daily `MISSION_DAY` embeds post to `#artemis-mission` at 14:00 UTC for each day
- `SPLASHDOWN` posts to `#artemis-alerts` with role ping and Pacific Ocean Google Maps link
- No duplicate embeds fire for any event after a process restart
- `.env` is absent from the GitHub repository; `.env.example` is present with all variable names
- `--dry-run` completes without errors on both local machine and Linode server before first live run
- `TRACKER_ONLINE` embed fires in `#artemis-alerts` immediately after the service starts on the Linode server
- Service survives a simulated reboot (`sudo reboot`) and resumes automatically without manual intervention

---

## Potential Risks and Mitigations

1. **NET shift invalidates pre-scheduled milestones** — All timeline milestones are relative to `net`. On any `NETShifted` event, all downstream scheduled triggers are cancelled and recomputed against the new value before rescheduling.

2. **LL2 `webcast_live` flag lags by minutes** — Independently resolved by the YouTube API poller (Task 11). Duplicate suppression ensures only the first-detected source fires the embed.

3. **SNAPI duplicate articles across polls** — Resolved by persisting the highest-seen article `id` and filtering client-side on `id > last_seen_id`.

4. **Hold message edit failure after restart** — If the held Discord message ID is lost, fall back to posting a new hold update embed rather than editing. Log a warning.

5. **LL2 API outage during launch window** — Cached timeline schedule continues firing. A single data-source warning posts to `#artemis-alerts`. Subsequent poll failures are silent until resolved.

6. **Webhook rate limit burst** — If multiple events trigger simultaneously (e.g., liftoff + status change + milestone all at once), the 1-second delay between webhook posts to the same channel ensures the 30 req/min ceiling is not hit.

7. **Secrets accidentally committed to GitHub** — Mitigated by `.gitignore` excluding `.env` and `state.json` before the first commit (Task 25). Run `git status` and `git diff --cached` to verify no secrets are staged before any `git push`.

8. **Linode server loses state file on redeploy** — The state file path should point to a location outside the cloned repo directory (e.g., `~/artemis-state.json`) so that `git pull` and service restarts never overwrite it. Alternatively, back up the state file before any `git pull` that changes the state schema.

---

## Alternative Approaches

1. **LL2 WebSocket push (Launch Library Plus)** — Eliminates all polling. Delivers push events the moment the database changes. Cleanest architecture but requires a paid subscription and persistent WebSocket connection management.

2. **NASA+ HLS stream probing** — Probe the HLS `.m3u8` manifest availability to detect the broadcast going live without a YouTube API key, as a pure fallback.

3. **Zapier / Make (no-code)** — Monitors LL2 on a schedule and routes to Discord. Zero infrastructure overhead but cannot support milestone scheduling, hold duration editing, or multi-channel routing at this granularity.

---

## API Reference Quick Sheet

| API | Endpoint | Auth | Cost |
|---|---|---|---|
| LL2 Launch Detail | `GET https://ll.thespacedevs.com/2.3.0/launches/41699701-2ef4-4b0c-ac9d-6757820cde87/` | None | Free: 15 req/hr |
| LL2 Events | `GET https://ll.thespacedevs.com/2.3.0/events/upcoming/?search=artemis` | None | Free: 15 req/hr (shared) |
| YouTube Videos | `GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo` | API Key | 1 unit/call, 10k/day free |
| YouTube Search (fallback) | `GET https://www.googleapis.com/youtube/v3/search?channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video` | API Key | 100 units/call |
| Spaceflight News | `GET https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&ordering=-published_at` | None | Free |
| Discord Webhook POST | `POST https://discord.com/api/webhooks/{id}/{token}` | Webhook URL | Free |
| Discord Webhook PATCH | `PATCH https://discord.com/api/webhooks/{id}/{token}/messages/{message_id}` | Webhook URL | Free |
