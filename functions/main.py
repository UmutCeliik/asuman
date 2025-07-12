# cloud-function-orchestrator/main.py

from firebase_functions import scheduler_fn, options
import requests
import time
from datetime import datetime
import random
import pytz
import os
import logging
import json # Loglama için eklendi

# Gelişmiş loglama için formatı ayarla
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - Orchestrator - %(message)s')

from state_manager import get_bot_state, set_bot_state, schedule_sleep

# Global ayarlar
options.set_global_options(timeout_sec=540, memory=options.MemoryOption.MB_512, region="europe-west1")
TZ = pytz.timezone('Europe/Istanbul')

# --- Değişkenler ---
# Cloud Run servisinizin URL'sini buraya yapıştırın
INSTA_WORKER_URL = "https://instagram-worker-service-xxxxxxxx-ew.a.run.app"
# Bu token, Cloud Function'a ortam değişkeni olarak atanmalıdır.
ORCHESTRATOR_SECRET_TOKEN = os.environ.get("ORCHESTRATOR_SECRET_TOKEN")


@scheduler_fn.on_schedule(schedule="every 15 minutes")
def orchestrate_bot_activity(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Her 15 dakikada bir çalışarak botun ne yapacağına karar veren ana fonksiyon.
    """
    now = datetime.now(TZ)
    state = get_bot_state()

    # 1. Uyku Modu Kontrolü
    if state.get("is_sleeping", False):
        wake_up_time = state.get("wake_up_at")
        if wake_up_time and now >= wake_up_time.astimezone(TZ):
            logging.info("🌞 Günaydın! Uyanma vakti geldi. Bot aktif ediliyor.")
            set_bot_state({"is_sleeping": False, "wake_up_at": None, "sleep_scheduled_at": None})
            trigger_worker_action("/process-and-get-new-messages")
        else:
            wake_up_str = wake_up_time.strftime('%H:%M') if wake_up_time else 'Bilinmiyor'
            logging.info(f"😴 Bot şu an uykuda. Uyanma saati: {wake_up_str}. İşlem yapılmıyor.")
            return

    # 2. Uyku Zamanı Geldi mi?
    elif now.hour >= 22 and not state.get("sleep_scheduled_at"):
         schedule_sleep()
         return

    # 3. Hangi Eylem Yapılacak?
    if random.random() < 0.15:
        logging.info("🎲 Rastgele seçim: Derin Gezinme Modu başlatılıyor...")
        trigger_worker_action("/deep-browse-session")
    else:
        logging.info("🎲 Rastgele seçim: Yeni mesajlar kontrol ediliyor...")
        trigger_worker_action("/process-and-get-new-messages")


def trigger_worker_action(endpoint_path: str):
    """
    Belirtilen endpoint'i Cloud Run üzerinde tetikler ve loglama yapar.
    """
    if not ORCHESTRATOR_SECRET_TOKEN:
        logging.error("ORCHESTRATOR_SECRET_TOKEN ortam değişkeni ayarlanmamış. İşlem iptal edildi.")
        return

    time.sleep(random.uniform(5, 45))
    headers = {"X-Orchestrator-Token": ORCHESTRATOR_SECRET_TOKEN}
    full_url = f"{INSTA_WORKER_URL}{endpoint_path}"
    
    # İSTEK LOGLAMASI: İşçi servisine giden isteği detaylı olarak logla
    logging.info(f"--> [İSTEK GÖNDERİLİYOR] URL: {full_url}, Method: GET")

    try:
        # Mesaj işleme endpoint'i için farklı mantık
        if "process-and-get-new-messages" in endpoint_path:
            response = requests.get(full_url, headers=headers, timeout=240)
            response.raise_for_status() # Hatalı durum kodlarında (4xx, 5xx) exception fırlatır
            
            # CEVAP LOGLAMASI: İşçi servisinden gelen cevabı detaylı olarak logla
            try:
                response_data = response.json()
                logging.info(f"<-- [CEVAP ALINDI] Status: {response.status_code}, Veri: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError:
                logging.error(f"<-- [CEVAP ALINDI] Status: {response.status_code}, Ancak cevap JSON formatında değil. Body: {response.text}")
                return

            yeni_mesajlar = response_data.get("new_messages", [])
            if yeni_mesajlar:
                process_messages_in_firestore(yeni_mesajlar)
            else:
                logging.info("✅ İşlenecek yeni mesaj bulunamadı.")
        
        # Diğer eylemler için sadece tetikle ve bekleme
        else:
            response = requests.get(full_url, headers=headers, timeout=10)
            response.raise_for_status()
            logging.info(f"<-- [EYLEM TETİKLENDİ] URL: {full_url}, Status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ HATA: Worker servisine ulaşılamadı: {e}")


def process_messages_in_firestore(messages: list):
    """
    İşçi servisinden gelen mesaj listesini alır ve Firestore'a işler.
    Bu fonksiyon, projenin veritabanı ile tek etkileşim noktasıdır.
    """
    from state_manager import DB
    from firebase_admin import firestore
    
    logging.info(f"🔥 {len(messages)} adet mesaj Firestore'a işlenmek üzere alındı.")
    
    for msg in messages:
        username = msg.get('username')
        message_text = msg.get('text')
        message_id = msg.get('message_id')

        # Gerekli verilerin hepsi mevcut mu diye kontrol et
        if not all([username, message_text, message_id]):
            logging.warning(f"Eksik veri içeren mesaj atlanıyor: {msg}")
            continue

        doc_ref = DB.collection("danisanlar").document(username)
        doc = doc_ref.get()

        if doc.exists:
            # Danışan zaten var, bu mesaj daha önce işlenmiş mi diye kontrol et
            processed_ids = doc.to_dict().get("processedMessageIds", [])
            if message_id in processed_ids:
                logging.info(f"   -> Mesaj ({message_id}) zaten işlenmiş, atlanıyor: {username}")
                continue
            
            logging.info(f"   -> MEVCUT DANIŞAN için yeni mesaj işleniyor: {username}")
            handle_existing_user_message(doc_ref, message_text, message_id)
        else:
            # Danışan yeni, profilini oluştur ve analiz et
            logging.info(f"   -> YENİ DANIŞAN bulundu ve kaydediliyor: {username}")
            analyze_and_save_profile_logic(username, message_text, message_id)
    
    logging.info("🔥 Tüm mesajların Firestore'a işlenmesi tamamlandı.")


def handle_existing_user_message(doc_ref, message_text: str, message_id: str):
    """Mevcut bir danışanın dökümanına yeni mesajı ekler."""
    from state_manager import TZ
    from firebase_admin import firestore
    try:
        doc_ref.update({
            "mesajGecmisi": firestore.ArrayUnion([{"mesaj": message_text, "tarih": datetime.now(TZ), "gonderen": "danisan"}]),
            "processedMessageIds": firestore.ArrayUnion([message_id]),
            "sonGorulme": datetime.now(TZ),
            "statu": "tekrar_yazdi"  # Okunmamış mesaj olduğunu belirtmek için statü güncelle
        })
        logging.info(f"      ✅ BAŞARILI: '{doc_ref.id}' için yeni mesaj eklendi.")
    except Exception as e:
        logging.error(f"      ❌ HATA: Mevcut danışan '{doc_ref.id}' güncellenirken: {e}")


def analyze_and_save_profile_logic(username: str, message: str, message_id: str):
    """Yeni danışan için Firestore'da yeni bir döküman oluşturur."""
    from state_manager import DB, TZ
    from firebase_admin import firestore
    
    # Gerçek bir LLM ile analiz için bu kısmı genişletebilirsiniz.
    analysis_data = {
        "etiketler": ["ilk_temas", "merakli"],
        "profilOzeti": "İlk kez mesaj atan ve hizmetler hakkında bilgi almak isteyen potansiyel danışan."
    }

    doc_ref = DB.collection("danisanlar").document(username)
    try:
        doc_ref.set({
          "instagramKullaniciAdi": username,
          "ilkTemasTarihi": datetime.now(TZ),
          "statu": "yeni_mesaj_var", # Yeni ve okunmamış mesaj olduğunu belirt
          "sonGorulme": datetime.now(TZ),
          "etiketler": analysis_data.get("etiketler", []),
          "profilOzeti": analysis_data.get("profilOzeti", ""),
          "mesajGecmisi": [{"mesaj": message, "tarih": datetime.now(TZ), "gonderen": "danisan"}],
          "processedMessageIds": [message_id] # İlk mesajın ID'si ile listeyi başlat
        }, merge=True) # `merge=True` olası race condition'ları engeller
        logging.info(f"      ✅ BAŞARILI: '{username}' Firestore'a yeni danışan olarak kaydedildi.")
    except Exception as e:
        logging.error(f"      ❌ HATA: Yeni danışan '{username}' kaydedilirken: {e}")

