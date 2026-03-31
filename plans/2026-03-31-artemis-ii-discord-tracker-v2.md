# Artemis II Discord Launch Tracker

## Objective

Build a polling service that monitors the Artemis II mission in real time using The Space Devs Launch Library 2 (LL2) API as the primary data source, augments it with the YouTube Data API v3 for live-stream detection and the Spaceflight News API for coverage articles, and pushes formatted Discord embeds via webhook to a target channel. The service covers the full mission arc: pre-launch countdown through splashdown (~10 days, April 1–11, 2026).

---

## Live Mission Data (Confirmed via API as of 2026-03-31)


| Field                 | Value                                                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Launch ID             | `41699701-2ef4-4b0c-ac9d-6757820cde87`                                                                                            |
| Status                | **Go for Launch** (status ID 1)                                                                                                   |
| NET (T-0)             | `2026-04-01T22:24:00Z` (6:24 PM EDT)                                                                                              |
| Launch Window         | 22:24 UTC – 00:24 UTC (2 hours)                                                                                                   |
| Weather Probability   | **80% GO**                                                                                                                        |
| Weather Concerns      | Cumulus Cloud Rule, Thick Cloud Layers Rule, Ground Winds                                                                         |
| Pad                   | Launch Complex 39B, Kennedy Space Center                                                                                          |
| YouTube Broadcast     | `https://www.youtube.com/watch?v=Tf_UjBMIzNo` (starts 16:50 UTC)                                                                  |
| NASA+ Broadcast       | `https://plus.nasa.gov/scheduled-video/nasas-artemis-ii-crew-launches-to-the-moon-official-broadcast/`                            |
| Mission Patch         | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/mission_patch_images/artemis2520ii_mission_patch_20250404074145.png` |
| Infographic           | `https://thespacedevs-prod.nyc3.digitaloceanspaces.com/media/infographic_images/sls2520block2_infographic_20260329082241.jpeg`    |
| FlightClub Trajectory | `https://flightclub.io/result?llId=41699701-2ef4-4b0c-ac9d-6757820cde87`                                                          |
| Splashdown            | Pacific Ocean, ~T+9d 1h 46m                                                                                                       |


**Crew (all data available in LL2 API):**


| Name           | Role               | Agency       | Twitter          |
| -------------- | ------------------ | ------------ | ---------------- |
| Reid Wiseman   | Commander          | NASA         | @astro_reid      |
| Victor Glover  | Pilot              | NASA         | @VicGlover       |
| Christina Koch | Mission Specialist | NASA         | @Astro_Christina |
| Jeremy Hansen  | Mission Specialist | CSA (Canada) | @Astro_Jeremy    |


**Notable firsts:**

- First crewed Artemis mission
- First humans beyond low Earth orbit since Apollo 17 (December 1972 — over 53 years)
- First Canadian to leave Earth orbit ever

---

## Data Sources & API Reference

### 1. The Space Devs Launch Library 2 (LL2) — PRIMARY SOURCE

**Base URL:** `https://ll.thespacedevs.com/2.2.0/`  
**Auth:** None required (free tier: 15 req/hour)


| Endpoint                                            | Purpose                                                                                     |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `GET /launch/41699701-2ef4-4b0c-ac9d-6757820cde87/` | Full launch detail: status, NET, probability, vidURLs, timeline, crew, patches, infographic |
| `GET /event/upcoming/?search=artemis&limit=10`      | Upcoming mission events: briefings, downlinks, news conferences                             |


**Fields monitored:**


| Field                       | Trigger                                                                                    |
| --------------------------- | ------------------------------------------------------------------------------------------ |
| `status.id`                 | Alert on change: 1=Go, 2=TBD, 3=Success, 4=Failure, 5=Hold, 6=In Flight, 7=Partial Failure |
| `net`                       | Alert when NET shifts (scrub/recycle/recalculate)                                          |
| `probability`               | Alert when weather probability changes                                                     |
| `weather_concerns`          | Include in weather update embeds                                                           |
| `webcast_live`              | Alert when flips `true`                                                                    |
| `vidURLs`                   | Extract YouTube stream URL dynamically each poll                                           |
| `holdreason` / `failreason` | Include in hold/scrub embeds                                                               |
| `updates[]`                 | Monitor for new entries (new weather forecasts, status notes from editors)                 |


### 2. YouTube Data API v3 — LIVE STREAM DETECTION

**Endpoint:** `GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo&key=YOUR_KEY`

**Fields monitored:**


| Field                                    | Trigger                                    |
| ---------------------------------------- | ------------------------------------------ |
| `snippet.liveBroadcastContent`           | `"live"` fires STREAM_LIVE embed           |
| `liveStreamingDetails.actualStartTime`   | Confirms stream start timestamp            |
| `liveStreamingDetails.concurrentViewers` | Included in periodic "stream stats" embeds |


**Quota:** 1 unit/call, 10,000/day free. Polling every 60 seconds for 6 hours = 360 units. Well within quota.

**Fallback discovery:** If `vidURLs` in the LL2 response contains no YouTube entry, use `search.list` on NASA's channel (`channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video`) to auto-discover the active stream.

### 3. Spaceflight News API (SNAPI) — NEWS FEED

**Endpoint:** `GET https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&limit=5&ordering=-published_at`  
**Auth:** None. Free. No rate limit documented.

Returns articles from major space outlets (NASASpaceFlight.com, Spaceflight Now, SpaceNews, Ars Technica, etc.) with title, URL, image, summary, and `publishedAt` timestamp. The response includes a `newsSite` field for the source name.

**Strategy:** Poll every 30 minutes. Store the `id` of the most recently seen article. On each poll, filter for articles with `id` greater than the stored value and post any new ones as `NEWS` embeds.

### 4. Discord Webhook API

**Endpoint:** `POST https://discord.com/api/webhooks/{webhook_id}/{webhook_token}`  
**Edit existing message:** `PATCH https://discord.com/api/webhooks/{id}/{token}/messages/{message_id}`  
Supports rich embeds with title, description, color, fields (up to 25), thumbnail, image, timestamp, and footer. Rate limit: 30 req/minute per webhook.

---

## Polling Schedule (≤ 15 req/hour budget)


| Phase                       | Window                               | Interval     | Req/hour      |
| --------------------------- | ------------------------------------ | ------------ | ------------- |
| Distant pre-launch          | > 24h before NET                     | Every 30 min | 2             |
| Near pre-launch             | 3h – 24h before NET                  | Every 10 min | 6             |
| Final approach              | 1h – 3h before NET                   | Every 8 min  | ~7            |
| Launch window               | < 1h before NET through window close | Every 4 min  | 15 (at limit) |
| Post-launch, mission active | Liftoff through splashdown           | Every 15 min | 4             |
| Mission complete            | After splashdown confirmed           | Every 30 min | 2             |


Note: The SNAPI news poll and LL2 events poll each run independently on a fixed 30-minute interval and are counted separately from the main launch detail poll.

---

## Implementation Plan

### Phase 1 — Project Scaffold & Configuration

- Task 1. **Define configuration schema** — store in env vars or a config file: LL2 launch ID, YouTube API key, YouTube video ID, Discord webhook URL, Discord role ID to ping on critical events (stream live, liftoff), polling intervals per phase, and milestone notification opt-in flags.
- Task 2. **Set up project dependencies** — select a runtime (Python with `httpx` + `APScheduler` recommended, or Node.js with `axios` + `node-cron`). Add an HTTP client, a scheduler, and a JSON-based state store library.
- Task 3. **Implement a persistent state store** — use a local JSON file or SQLite to persist: last-known `status.id`, `net`, `probability`, `webcast_live`, the ID of the last-seen SNAPI article, and a log of all previously fired notification keys (for duplicate suppression). This ensures restarts do not re-fire past alerts.

### Phase 2 — LL2 Poller

- Task 4. **Implement the LL2 launch detail fetcher** — call `GET /launch/{id}/` and deserialize into a typed data model. On HTTP 429 (rate limited), back off for the duration specified in the `Retry-After` header and skip that cycle without failing.
- Task 5. **Implement change detection** — compare freshly fetched state against the state store and emit typed internal events for each detected change: `StatusChanged`, `NETShifted`, `ProbabilityChanged`, `WebcastWentLive`, `HoldIssued`, `NewUpdateEntry`.
- Task 6. **Implement adaptive polling scheduler** — schedule the LL2 fetch function at the intervals defined in the polling table above. Recalculate which phase applies on every tick based on `now` vs. the current stored `net`. When `net` changes, recalculate phase immediately.
- Task 7. **Implement timeline milestone extractor** — on first successful fetch, parse the `timeline` array. Compute each milestone's absolute UTC timestamp by adding its `relative_time` ISO 8601 duration offset to the confirmed `net`. Store these as a sorted list of scheduled notification triggers. If `net` changes due to a hold or recycle, recompute and reschedule all downstream milestone times.
- Task 8. **Implement the LL2 events poller** — call `GET /event/upcoming/?search=artemis&limit=10` every 30 minutes. On each poll, compare the returned event IDs against the state store. Post new events as `MISSION_EVENT` embeds. This covers daily briefings, live crew downlinks, post-launch news conferences, and lunar flyby activities.
- Task 9. **Implement 45th Weather Squadron update monitor** — on each LL2 launch fetch, scan the `updates` array for any new entries (compare the latest `id` against the stored value). When a new update entry contains a 45th Weather Squadron forecast PDF URL, post it as a `WEATHER_UPDATE` embed with a direct link to the PDF.

### Phase 3 — YouTube Live Stream Monitor

- Task 10. **Implement the YouTube video status poller** — call `GET /videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo` every 60 seconds starting 3 hours before NET. Monitor `liveBroadcastContent` for the transition from `"upcoming"` to `"live"`. This runs independently of the LL2 `webcast_live` flag and has no human-editor lag.
- Task 11. **Implement live stream discovery fallback** — if the LL2 `vidURLs` field contains no YouTube entry, query the NASA YouTube channel (`channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video`) to auto-discover any active NASA broadcast and extract its video ID.
- Task 12. **Implement concurrent viewer tracking** — once the stream is confirmed live, poll `liveStreamingDetails.concurrentViewers` every 10 minutes and include the figure in a periodic "now watching" line within the mission status embed.

### Phase 4 — Spaceflight News API Poller

- Task 13. **Implement the SNAPI news fetcher** — call `GET /v4/articles/?search=Artemis+II&limit=5&ordering=-published_at` every 30 minutes. On each poll, compare returned article IDs against the stored last-seen ID. For each new article, post a `NEWS` embed containing the article title, source site name, short summary, thumbnail image, and a direct link.

### Phase 5 — Discord Webhook Notification Engine

- Task 14. **Define the embed template library** — create distinct, color-coded embed templates for each notification category:
  - `CREW_INTRO` (deep blue): mission patch thumbnail, crew roster with roles, bios, Twitter links, FlightClub trajectory link — posted at T-24h
  - `LAUNCH_COUNTDOWN` (blue): T-24h, T-3h, T-1h, T-30m, T-10m with NET, weather %, stream links, mission patch thumbnail
  - `STATUS_CHANGE` (yellow=hold, green=go-confirmed, red=scrub/failure)
  - `HOLD_UPDATE` (orange): posted every 15 minutes while a hold is active, showing hold duration; delivered by editing the existing hold message rather than posting a new one
  - `STREAM_LIVE` (bright green): fires on YouTube `"live"` detection or LL2 `webcast_live` flip (whichever is first); includes video link, thumbnail, and a role @mention ping
  - `WEATHER_UPDATE` (orange): fires when probability changes or new 45th Weather Squadron forecast is available
  - `MILESTONE` (purple): countdown and post-launch timeline events, with a Mission Elapsed Time (MET) field in the footer post-liftoff
  - `HISTORICAL_MILESTONE` (gold): special high-visibility embeds for the three historic firsts — first humans beyond LEO since 1972, first Canadian beyond LEO, mission patch as thumbnail
  - `MISSION_EVENT` (teal): daily briefings, crew downlinks, post-launch news conferences from the LL2 events endpoint
  - `NEWS` (grey): Spaceflight News API articles with source name, headline, summary, and thumbnail
  - `MISSION_DAY` (indigo): daily mission day summary embeds
  - `SPLASHDOWN` (green): final embed with Pacific Ocean recovery location, total mission duration, and Google Maps link
- Task 15. **Implement the webhook POST and PATCH functions** — construct Discord JSON payloads with the `embeds` array. For new messages, use `POST`. For in-place updates (hold duration, live viewer count), store the returned Discord message ID and use `PATCH /webhooks/{id}/{token}/messages/{message_id}` to edit rather than posting duplicates. Add a 1-second inter-message delay between sequential posts.
- Task 16. **Implement duplicate suppression** — before posting any notification, check the state store for a composite key of `(event_type, field_value, utc_timestamp_bucket)`. If a match exists, skip. This prevents re-firing after restarts.
- Task 17. **Implement role @mention injection** — for `STREAM_LIVE` and liftoff `MILESTONE` embeds, prepend the Discord `content` field (outside the embed) with `<@&ROLE_ID>` to ping the configured role. All other notifications use embed-only messaging with no ping.

### Phase 6 — Countdown & Mission Scheduler

- Task 18. **Schedule fixed pre-launch countdown embeds** — using confirmed NET `2026-04-01T22:24:00Z`, pre-schedule:
  - T-24h → `2026-03-31T22:24:00Z`: post `CREW_INTRO` + `LAUNCH_COUNTDOWN` pair
  - T-3h → `2026-04-01T19:24:00Z`: `LAUNCH_COUNTDOWN` with weather update
  - T-1h → `2026-04-01T21:24:00Z`: `LAUNCH_COUNTDOWN` with stream link prominent
  - T-30m → `2026-04-01T21:54:00Z`: `LAUNCH_COUNTDOWN`
  - T-10m → `2026-04-01T22:14:00Z`: `LAUNCH_COUNTDOWN` with liftoff imminent language
  - All reschedule automatically if `net` changes.
- Task 19. **Schedule key launch-phase milestone embeds** — using computed absolute times from the `timeline` array:
  - Propellant loading GO (T-10h 50m)
  - Flight crew to pad (T-4h 40m)
  - Crew boarding Orion (T-4h)
  - Hatch closure (T-3h 40m)
  - Terminal count start (T-10m)
  - Liftoff / SRB ignition (T-0) — fires on confirmed `status.id == 6` (In Flight) or scheduled time
  - Max-Q (T+1m 10s)
  - SRB separation (T+2m 8s)
  - MECO (T+8m 6s)
  - Orion solar array deployment (T+20m)
  - Orion/ICPS separation (T+3h 24m)
- Task 20. **Schedule trans-lunar and mission milestone embeds** — key post-launch events as `MILESTONE` and `HISTORICAL_MILESTONE`:
  - Translunar injection burn (MET +1d 1h 37m): post as `HISTORICAL_MILESTONE` — "First humans leaving Earth orbit since Apollo 17, December 1972"
  - Orion enters lunar sphere of influence (MET +4d 7h): `MILESTONE`
  - Lunar flyby begins (MET +4d 22h): `HISTORICAL_MILESTONE` — "First humans near the Moon since 1972. First Canadian in lunar vicinity ever."
  - Lunar closest approach (MET +5d 1h 23m): `HISTORICAL_MILESTONE` with closest approach distance note
  - Max distance from Earth (MET +5d 1h 26m): `HISTORICAL_MILESTONE` — "Humans are now at their maximum distance from Earth on this mission"
  - Orion exits lunar sphere of influence (MET +5d 19h 47m): `MILESTONE`
  - Atmospheric entry (MET +9d 1h 33m): `MILESTONE`
  - Splashdown (MET +9d 1h 46m): `SPLASHDOWN` embed
- Task 21. **Schedule daily Mission Day embeds** — post once per day at 14:00 UTC starting Mission Day 2 (April 3) through splashdown day. Each embed lists the mission day number, current mission phase, MET, and the next 2–3 notable activities from the timeline for that day.
- Task 22. **Implement hold duration tracker** — when `status.id` changes to 5 (Hold), record the hold start time and post an initial `HOLD_UPDATE` embed. Every 15 minutes thereafter, edit that same Discord message using its stored message ID to update the "Hold duration: X minutes" field. When `status.id` returns to 1, post a "Hold lifted — countdown resuming" status embed and stop the hold timer. Reschedule all downstream milestones.

### Phase 7 — Resilience & Deployment

- Task 23. **Implement graceful error handling** — all HTTP calls catch network errors, non-2xx responses, and JSON parse failures. On error, log it, emit a warning, and skip the cycle. If LL2 is unreachable for more than 30 minutes during the active launch window, post a single `STATUS_CHANGE` embed noting "Data source temporarily unavailable" and resume silently once connectivity returns.
- Task 24. **Implement a startup announcement embed** — on first run, post a `LAUNCH_COUNTDOWN` embed confirming the tracker is online, current status (Go for Launch), NET, weather probability, stream link, and mission patch thumbnail.
- Task 25. **Write a process management wrapper** — use `systemd`, `pm2` (Node), or `supervisor` (Python) to run the service as a background process with automatic restart on crash.
- Task 26. **Implement `--dry-run` mode** — replaces all Discord webhook POSTs/PATCHes with console output. Runs full polling and detection logic against live APIs so the entire pipeline can be verified end-to-end without posting to the channel.

---

## Verification Criteria

- Polling the LL2 launch endpoint returns `status.abbrev == "Go"` before launch
- A status change to Hold (ID 5) fires a hold embed within the next 4-minute polling cycle, and the hold duration counter updates every 15 minutes by editing that message in place
- The YouTube `liveBroadcastContent == "live"` transition fires a `STREAM_LIVE` embed with the confirmed URL independent of the LL2 `webcast_live` flag
- All T-minus countdown embeds fire within 60 seconds of their scheduled time
- The TLI burn fires a `HISTORICAL_MILESTONE` embed with first-humans-beyond-LEO context
- The lunar closest approach fires a `HISTORICAL_MILESTONE` embed with first-Canadian-beyond-LEO context
- Daily `MISSION_DAY` embeds post at 14:00 UTC for each of the 9 mission days
- The `SPLASHDOWN` embed fires and includes a Pacific Ocean Google Maps link
- New SNAPI articles post as `NEWS` embeds within 30 minutes of publication
- No duplicate embeds fire for any event after a process restart

---

## Potential Risks and Mitigations

1. **Launch hold causes missed milestones** — All timeline milestones are computed relative to `net`. When `net` changes (hold or recycle), all downstream scheduled triggers are cancelled and recomputed against the new `net` value before being rescheduled.
2. **LL2 `webcast_live` flag lags by minutes** — The LL2 flag is manually updated by community editors. The independent YouTube API poller in Task 10 resolves this with no human-editor lag. Whichever fires first wins; the other is suppressed as a duplicate.
3. **SNAPI returning duplicate articles across polls** — Resolved by persisting the highest-seen article `id` in the state store and filtering on `id > last_seen_id` client-side.
4. **Discord message edit failures on hold updates** — If the original hold message ID is lost (e.g., after a restart), fall back to posting a new hold update embed rather than editing. Log a warning.
5. **LL2 API temporary outage during launch window** — The last successful response is cached. If LL2 is unreachable, the timeline milestone scheduler continues firing pre-computed milestones from the cached schedule. A single "data source unavailable" notice is posted; subsequent failures are silent until resolved.

---

## Alternative Approaches

1. **LL2 WebSocket push (Launch Library Plus)** — Eliminates all polling entirely. LL2 Plus delivers push events the moment the database changes. Cleanest architecture but requires a paid subscription and persistent WebSocket connection management.
2. **NASA+ HLS stream probing** — The NASA+ broadcast has an HLS `.m3u8` URL. Probing its availability can detect when the stream goes live without a YouTube API key, as a pure fallback.
3. **Zapier / Make (no-code)** — Can monitor the LL2 API on a schedule and route to Discord with zero infrastructure. Trades granularity and milestone scheduling for zero-code deployment.

---

## API Reference Quick Sheet


| API                   | Endpoint                                                                                                        | Auth        | Cost                      |
| --------------------- | --------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------- |
| LL2 Launch Detail     | `GET https://ll.thespacedevs.com/2.2.0/launch/41699701-2ef4-4b0c-ac9d-6757820cde87/`                            | None        | Free: 15 req/hr           |
| LL2 Events            | `GET https://ll.thespacedevs.com/2.2.0/event/upcoming/?search=artemis`                                          | None        | Free: 15 req/hr (shared)  |
| YouTube Videos        | `GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=Tf_UjBMIzNo`             | API Key     | 1 unit/call, 10k/day free |
| YouTube Search        | `GET https://www.googleapis.com/youtube/v3/search?channelId=UCLA_DiR1FfKNvjuUpBHmylQ&eventType=live&type=video` | API Key     | 100 units/call            |
| Spaceflight News      | `GET https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&ordering=-published_at`                  | None        | Free                      |
| Discord Webhook POST  | `POST https://discord.com/api/webhooks/{id}/{token}`                                                            | Webhook URL | Free                      |
| Discord Webhook PATCH | `PATCH https://discord.com/api/webhooks/{id}/{token}/messages/{message_id}`                                     | Webhook URL | Free                      |


