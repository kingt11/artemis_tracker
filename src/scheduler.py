import asyncio
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import CONFIRMED_NET
from state import load_state, update_state
from poller_ll2 import poll_ll2, fetch_ll2_events
from poller_youtube import poll_youtube
from poller_snapi import poll_snapi

scheduler = AsyncIOScheduler()

def get_polling_interval(net_time):
    now = datetime.now(timezone.utc)
    delta = net_time - now
    
    if delta > timedelta(hours=24):
        return 30
    elif timedelta(hours=3) <= delta <= timedelta(hours=24):
        return 10
    elif timedelta(hours=1) <= delta < timedelta(hours=3):
        return 8
    elif timedelta(hours=-2) <= delta < timedelta(hours=1):
        return 4
    elif timedelta(days=-10) <= delta < timedelta(hours=-2):
        return 15
    else:
        return 30

async def adaptive_ll2_poll():
    await poll_ll2()
    
    state = load_state()
    net_str = state.get("last_net") or CONFIRMED_NET
    try:
        net_time = datetime.fromisoformat(net_str.replace("Z", "+00:00"))
    except ValueError:
        net_time = datetime.now(timezone.utc) + timedelta(days=1)
        
    interval = get_polling_interval(net_time)
    
    # Reschedule with new interval
    scheduler.reschedule_job("ll2_poll_job", trigger=IntervalTrigger(minutes=interval))

def setup_scheduler():
    state = load_state()
    net_str = state.get("last_net") or CONFIRMED_NET
    try:
        net_time = datetime.fromisoformat(net_str.replace("Z", "+00:00"))
    except ValueError:
        net_time = datetime.now(timezone.utc) + timedelta(days=1)
        
    interval = get_polling_interval(net_time)
    
    scheduler.add_job(adaptive_ll2_poll, IntervalTrigger(minutes=interval), id="ll2_poll_job", next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(fetch_ll2_events, IntervalTrigger(minutes=30), id="ll2_events_job", next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(poll_snapi, IntervalTrigger(minutes=30), id="snapi_job", next_run_time=datetime.now(timezone.utc))
    
    # YouTube polling
    now = datetime.now(timezone.utc)
    if net_time - now <= timedelta(hours=3):
        scheduler.add_job(poll_youtube, IntervalTrigger(seconds=60), id="youtube_job", next_run_time=datetime.now(timezone.utc))
        
    scheduler.start()
