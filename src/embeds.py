from datetime import datetime

# Colors
COLORS = {
    "TRACKER_ONLINE": 0x808080,
    "CREW_INTRO": 0x003087,
    "LAUNCH_COUNTDOWN": 0x1E6BE6,
    "STATUS_CHANGE_HOLD": 0xFFD700,
    "STATUS_CHANGE_GO": 0x00CC44,
    "STATUS_CHANGE_SCRUB": 0xFF2200,
    "HOLD_UPDATE": 0xFF8C00,
    "NET_SHIFT": 0xFF4500,
    "STREAM_LIVE": 0x00FF88,
    "WEATHER_UPDATE": 0xFF8C00,
    "MILESTONE": 0x7B2FBE,
    "HISTORICAL_MILESTONE": 0xFFB300,
    "MISSION_DAY": 0x3F51B5,
    "MISSION_EVENT": 0x008B8B,
    "NEWS": 0x606060,
    "SPLASHDOWN": 0x00CC44
}

def create_tracker_online(status, net, stream_link):
    return {
        "title": "Tracker Online",
        "description": "Artemis II Launch Tracker is now online.",
        "color": COLORS["TRACKER_ONLINE"],
        "fields": [
            {"name": "Status", "value": status, "inline": True},
            {"name": "NET", "value": net, "inline": True},
            {"name": "Stream", "value": stream_link, "inline": False}
        ]
    }

def create_status_change(status_name, description, reason, is_hold, is_scrub):
    color = COLORS["STATUS_CHANGE_HOLD"] if is_hold else (COLORS["STATUS_CHANGE_SCRUB"] if is_scrub else COLORS["STATUS_CHANGE_GO"])
    embed = {
        "title": f"Status Change: {status_name}",
        "description": description,
        "color": color
    }
    if reason:
        embed["fields"] = [{"name": "Reason", "value": reason, "inline": False}]
    return embed

def create_net_shift(old_net, new_net, delta):
    return {
        "title": "NET Shifted",
        "color": COLORS["NET_SHIFT"],
        "fields": [
            {"name": "Old NET", "value": old_net, "inline": True},
            {"name": "New NET", "value": new_net, "inline": True},
            {"name": "Delta", "value": delta, "inline": False}
        ]
    }

def create_hold_update(duration, reason):
    embed = {
        "title": "Hold Update",
        "description": f"Hold duration: {duration}",
        "color": COLORS["HOLD_UPDATE"]
    }
    if reason:
        embed["fields"] = [{"name": "Reason", "value": reason, "inline": False}]
    return embed

def create_stream_live(youtube_url, thumbnail, nasa_plus_url, viewers=None):
    embed = {
        "title": "Stream is LIVE",
        "url": youtube_url,
        "color": COLORS["STREAM_LIVE"],
        "fields": [
            {"name": "YouTube", "value": f"[Watch Here]({youtube_url})", "inline": True},
            {"name": "NASA+", "value": f"[Watch Here]({nasa_plus_url})", "inline": True}
        ]
    }
    if thumbnail:
        embed["thumbnail"] = {"url": thumbnail}
    if viewers:
        embed["fields"].append({"name": "Concurrent Viewers", "value": str(viewers), "inline": False})
    return embed

def create_weather_update(probability, concerns, pdf_link=None):
    embed = {
        "title": "Weather Update",
        "color": COLORS["WEATHER_UPDATE"],
        "fields": [
            {"name": "Probability", "value": f"{probability}% GO", "inline": True}
        ]
    }
    if concerns:
        embed["fields"].append({"name": "Concerns", "value": concerns, "inline": False})
    if pdf_link:
        embed["fields"].append({"name": "Forecast PDF", "value": f"[View PDF]({pdf_link})", "inline": False})
    return embed

def create_news(title, site, summary, url, image_url):
    embed = {
        "title": title,
        "url": url,
        "description": summary,
        "color": COLORS["NEWS"],
        "footer": {"text": site}
    }
    if image_url:
        embed["thumbnail"] = {"url": image_url}
    return embed
