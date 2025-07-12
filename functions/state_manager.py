# cloud-function-orchestrator/state_manager.py

import firebase_admin
from firebase_admin import firestore
from datetime import datetime, timedelta
import random
import pytz
import logging

# Firestore'a sadece bir kez bağlan
if not firebase_admin._apps:
    firebase_admin.initialize_app()

DB = firestore.client()
TZ = pytz.timezone('Europe/Istanbul')

def get_bot_state():
    """Botun mevcut durumunu Firestore'dan çeker."""
    doc_ref = DB.collection("bot_system_state").document("main_state")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {"is_sleeping": False, "wake_up_at": None}

def set_bot_state(state_updates: dict):
    """Botun durumunu Firestore'da günceller."""
    doc_ref = DB.collection("bot_system_state").document("main_state")
    state_updates["last_updated"] = datetime.now(TZ)
    doc_ref.set(state_updates, merge=True)
    logging.info(f"🤖 Bot durumu güncellendi: {state_updates}")

def schedule_sleep():
    """Bot için bir sonraki uyku ve uyanma zamanını planlar."""
    now = datetime.now(TZ)
    
    sleep_start_hour = random.randint(22, 23) # 22 veya 23
    sleep_time = now.replace(hour=sleep_start_hour, minute=random.randint(0, 59))
    if sleep_time < now: # Eğer saat geçmişse, ertesi gün için planla
        sleep_time += timedelta(days=1)

    wake_up_time = sleep_time.replace(hour=random.randint(7, 8), minute=random.randint(0, 59))
    if wake_up_time.hour < sleep_time.hour:
        wake_up_time += timedelta(days=1)
        
    set_bot_state({
        "is_sleeping": True,
        "sleep_scheduled_at": sleep_time,
        "wake_up_at": wake_up_time
    })
    logging.info(f"😴 Uyku planlandı. Bot {sleep_time.strftime('%Y-%m-%d %H:%M')} itibariyle uyuyacak ve {wake_up_time.strftime('%Y-%m-%d %H:%M')} saatinde uyanacak.")
