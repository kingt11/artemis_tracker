import asyncio
import traceback
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

async def safe_job(name, coro):
    """Wrapper that catches all exceptions so APScheduler never silently drops a job."""
    try:
        await coro()
    except Exception as e:
        print(f"[Scheduler] Job '{name}' failed: {type(e).__name__}: {e}")
        traceback.print_exc()

async def adaptive_ll2_poll():
    await safe_job("ll2_poll", poll_ll2)
    
    state = load_state()
    net_str = state.get("last_net") or CONFIRMED_NET
    try:
        net_time = datetime.fromisoformat(net_str.replace("Z", "+00:00"))
    except ValueError:
        net_time = datetime.now(timezone.utc) + timedelta(days=1)
        
    interval = get_polling_interval(net_time)
    
    try:
        scheduler.reschedule_job("ll2_poll_job", trigger=IntervalTrigger(minutes=interval))
        print(f"[Scheduler] LL2 poll interval: {interval} min")
    except Exception as e:
        print(f"[Scheduler] Error rescheduling LL2 job: {e}")

async def safe_ll2_events():
    await safe_job("ll2_events", fetch_ll2_events)

async def safe_snapi():
    await safe_job("snapi", poll_snapi)

async def safe_youtube():
    await safe_job("youtube", poll_youtube)

def setup_scheduler():
    state = load_state()
    net_str = state.get("last_net") or CONFIRMED_NET
    try:
        net_time = datetime.fromisoformat(net_str.replace("Z", "+00:00"))
    except ValueError:
        net_time = datetime.now(timezone.utc) + timedelta(days=1)
        
    interval = get_polling_interval(net_time)
    
    print(f"[Scheduler] Starting with LL2 interval={interval}min, SNAPI=30min, Events=30min")
    
    scheduler.add_job(adaptive_ll2_poll, IntervalTrigger(minutes=interval), id="ll2_poll_job", next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(safe_ll2_events, IntervalTrigger(minutes=30), id="ll2_events_job", next_run_time=datetime.now(timezone.utc))
    scheduler.add_job(safe_snapi, IntervalTrigger(minutes=30), id="snapi_job", next_run_time=datetime.now(timezone.utc))
    
    # YouTube polling
    now = datetime.now(timezone.utc)
    if net_time - now <= timedelta(hours=3):
        print("[Scheduler] Within 3h of NET, enabling YouTube polling (60s)")
        scheduler.add_job(safe_youtube, IntervalTrigger(seconds=60), id="youtube_job", next_run_time=datetime.now(timezone.utc))
    else:
        print(f"[Scheduler] YouTube polling deferred until T-3h (NET: {net_str})")
        
    scheduler.start()
    print("[Scheduler] All jobs started")
