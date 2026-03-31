import json
import os
from config import STATE_FILE_PATH

def load_state():
    if not os.path.exists(STATE_FILE_PATH):
        return {
            "last_status_id": None,
            "last_net": None,
            "last_probability": None,
            "last_webcast_live": None,
            "last_ll2_update_id": 0,
            "last_snapi_article_id": 0,
            "hold_start_utc": None,
            "hold_discord_message_id": None,
            "fired_notifications": [],
            "milestone_schedule": []
        }
    with open(STATE_FILE_PATH, 'r') as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE_PATH, 'w') as f:
        json.dump(state, f, indent=2)

def update_state(key, value):
    state = load_state()
    state[key] = value
    save_state(state)

def has_fired(composite_key):
    state = load_state()
    return composite_key in state.get("fired_notifications", [])

def mark_fired(composite_key):
    state = load_state()
    if "fired_notifications" not in state:
        state["fired_notifications"] = []
    if composite_key not in state["fired_notifications"]:
        state["fired_notifications"].append(composite_key)
        save_state(state)
