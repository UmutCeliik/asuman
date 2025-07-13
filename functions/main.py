# cloud-function-orchestrator/main.py (JSON Loglama ile Nihai Sürüm)

from firebase_functions import scheduler_fn, options
import requests
import time
from datetime import datetime
import random
import pytz
import os
import json 
from firebase_admin import firestore

# logging_config'i import ettiğimizde loglama otomatik olarak ayarlanır.
import logging
import logging_config as logging_config

from state_manager import get_bot_state, set_bot_state, schedule_sleep, get_db, TZ

# Artık tüm logları bu logger nesnesi üzerinden yapacağız.
# logging_config.setup_logging() # Loglama yapılandırma fonksiyonunu çağır

# Artık tüm logları bu logger nesnesi üzerinden yapacağız.
logger = logging.getLogger(__name__)

options.set_global_options(timeout_sec=540, memory=options.MemoryOption.MB_512, region="europe-west1")

INSTA_WORKER_URL = "https://instagram-worker-service-354658507685.europe-west1.run.app"
ORCHESTRATOR_SECRET_TOKEN = "AsmN-Insta-Bot-hY7zP9qV3rXbFwEaT8sU" # ÖNEMLİ: Bu değeri Secret Manager'a taşıyın.

@scheduler_fn.on_schedule(schedule="every 15 minutes")
def orchestrate_bot_activity(event: scheduler_fn.ScheduledEvent) -> None:
    logger.info("--- Orkestra Şefi Tetiklendi ---")
    try:
        db = get_db()
        control_doc_ref = db.collection("system_settings").document("main_controls")
        try:
            control_doc = control_doc_ref.get()
            if control_doc.exists and not control_doc.to_dict().get("isSchedulerActive", True):
                logger.info("ℹ️ Sistem arayüzden devre dışı bırakılmış. İşlem yapılmıyor.")
                return
        except Exception as e:
            logger.warning(f"Sistem kontrol ayarı okunurken hata oluştu, devam ediliyor.", exc_info=True)

        now = datetime.now(TZ)
        state = get_bot_state()
        logger.info("Mevcut bot durumu.", extra={'state': state})

        if state.get("is_sleeping", False):
            wake_up_time = state.get("wake_up_at")
            if wake_up_time and now >= wake_up_time.astimezone(TZ):
                logger.info("🌞 Günaydın! Uyanma vakti geldi. Bot aktif ediliyor.")
                set_bot_state({"is_sleeping": False, "wake_up_at": None, "sleep_scheduled_at": None})
                trigger_worker_action("/process-and-get-new-messages")
            else:
                wake_up_str = wake_up_time.strftime('%H:%M') if wake_up_time else 'Bilinmiyor'
                logger.info(f"😴 Bot şu an uykuda. Uyanma saati: {wake_up_str}. İşlem yapılmıyor.")
            return
        elif now.hour >= 22 and not state.get("sleep_scheduled_at"):
             logger.info("🌙 Gece oldu, uyku planlanıyor...")
             schedule_sleep()
             return

        action_choice = "Derin Gezinme" if random.random() < 0.15 else "Mesaj Kontrolü"
        logger.info(f"🎲 Rastgele seçim yapıldı: {action_choice}")

        if action_choice == "Derin Gezinme":
            trigger_worker_action("/deep-browse-session")
        else:
            trigger_worker_action("/process-and-get-new-messages")
            
    except Exception as e:
        logger.critical(f"❌ KRİTİK HATA: Orkestra Şefi fonksiyonu çöktü.", exc_info=True)
    finally:
        logger.info("--- Orkestra Şefi İşlemi Tamamladı ---")


def trigger_worker_action(endpoint_path: str):
    wait_time = random.uniform(5, 25)
    logger.info(f"İşçiyi çağırmadan önce {int(wait_time)} saniye bekleniyor...")
    time.sleep(wait_time)
    
    headers = {"X-Orchestrator-Token": ORCHESTRATOR_SECRET_TOKEN}
    full_url = f"{INSTA_WORKER_URL}{endpoint_path}"
    logger.info(f"--> [İSTEK GÖNDERİLİYOR] URL: {full_url}")
    
    try:
        response = requests.get(full_url, headers=headers, timeout=300)
        logger.info(f"<-- [CEVAP ALINDI] Status: {response.status_code}")
        response.raise_for_status() 
        
        try:
            response_data = response.json()
            logger.info("Gelen Veri işleniyor.", extra={'json_response': response_data})
            
            yeni_mesajlar = response_data.get("new_messages", [])
            if yeni_mesajlar:
                process_messages_in_firestore(yeni_mesajlar)
            else:
                logger.info("✅ İşçi (Worker) tarafından işlenecek yeni mesaj raporlanmadı.")

        except json.JSONDecodeError:
            logger.error(f"HATA: Cevap JSON formatında değil.", extra={'response_body': response.text})
            
    except requests.exceptions.RequestException as e:
        logger.error(f"HATA: Worker servisine ulaşılamadı.", exc_info=True)
    except Exception as e:
        logger.error(f"HATA: Worker işlemi sırasında beklenmedik bir hata.", exc_info=True)


def process_messages_in_firestore(messages: list):
    logger.info(f"🔥 {len(messages)} adet mesaj Firestore'a işlenmek üzere alındı.")
    db = get_db()
    
    for msg in messages:
        username = msg.get('username')
        message_id = msg.get('message_id')
        logger.info(f"-> Firestore için '{username}' kullanıcısının mesajı (ID: {message_id}) işleniyor...")

        if not all([username, msg.get('text'), message_id]):
            logger.warning(f"Eksik veri içeren mesaj atlanıyor.", extra={'message_data': msg})
            continue

        doc_ref = db.collection("danisanlar").document(username)
        
        try:
            doc = doc_ref.get()
            if doc.exists:
                processed_ids = doc.to_dict().get("processedMessageIds", [])
                if message_id in processed_ids:
                    logger.info(f"BU MESAJ ZATEN İŞLENMİŞ ({message_id}), atlanıyor: {username}")
                    continue
                
                logger.info(f"MEVCUT DANIŞAN için yeni mesaj veritabanına ekleniyor: {username}")
                doc_ref.update({
                    "mesajGecmisi": firestore.ArrayUnion([{"mesaj": msg.get('text'), "tarih": datetime.now(TZ), "gonderen": "danisan"}]),
                    "processedMessageIds": firestore.ArrayUnion([message_id]),
                    "sonGorulme": datetime.now(TZ),
                    "statu": "tekrar_yazdi"
                })
                logger.info(f"BAŞARILI: '{username}' güncellendi.")

            else:
                logger.info(f"YENİ DANIŞAN bulundu, veritabanına kaydediliyor: {username}")
                doc_ref.set({
                    "instagramKullaniciAdi": username,
                    "ilkTemasTarihi": datetime.now(TZ),
                    "statu": "yeni_mesaj_var",
                    "sonGorulme": datetime.now(TZ),
                    "etiketler": ["ilk_temas"],
                    "profilOzeti": "İlk kez mesaj atan potansiyel danışan.",
                    "mesajGecmisi": [{"mesaj": msg.get('text'), "tarih": datetime.now(TZ), "gonderen": "danisan"}],
                    "processedMessageIds": [message_id]
                })
                logger.info(f"BAŞARILI: '{username}' yeni danışan olarak kaydedildi.")
        except Exception as e:
            logger.error(f"HATA: '{username}' için Firestore işlemi sırasında hata.", exc_info=True)
    
    logger.info("🔥 Tüm mesajların Firestore'a işlenmesi tamamlandı.")