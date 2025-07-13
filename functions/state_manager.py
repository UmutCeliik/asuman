# cloud-function-orchestrator/state_manager.py

import firebase_admin
from firebase_admin import firestore
from datetime import datetime, timedelta
import random
import pytz
import logging

# Ana logger'ı alıyoruz
logger = logging.getLogger(__name__)

_db_client = None

def get_db():
    global _db_client
    if _db_client is None:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        _db_client = firestore.client()
    return _db_client

TZ = pytz.timezone('Europe/Istanbul')

def get_bot_state():
    db = get_db()
    doc_ref = db.collection("bot_system_state").document("main_state")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"is_sleeping": False, "wake_up_at": None}

def set_bot_state(state_updates: dict):
    db = get_db()
    doc_ref = db.collection("bot_system_state").document("main_state")
    state_updates["last_updated"] = datetime.now(TZ)
    doc_ref.set(state_updates, merge=True)
    logger.info(f"🤖 Bot durumu güncellendi.", extra={'new_state': state_updates})

def schedule_sleep():
    now = datetime.now(TZ)
    
    sleep_start_hour = random.randint(22, 23)
    sleep_time = now.replace(hour=sleep_start_hour, minute=random.randint(0, 59))
    if sleep_time < now:
        sleep_time += timedelta(days=1)

    wake_up_time = sleep_time.replace(hour=random.randint(7, 8), minute=random.randint(0, 59))
    if wake_up_time.hour < sleep_time.hour:
        wake_up_time += timedelta(days=1)
        
    state_to_set = {
        "is_sleeping": True,
        "sleep_scheduled_at": sleep_time,
        "wake_up_at": wake_up_time
    }
    set_bot_state(state_to_set)
    logger.info(f"😴 Uyku planlandı. Bot {sleep_time.strftime('%H:%M')} itibariyle uyuyacak ve {wake_up_time.strftime('%H:%M')} saatinde uyanacak.")
