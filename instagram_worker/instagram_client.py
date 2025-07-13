# instagram-worker/instagram_client.py (AttributeError Düzeltmesi ile Nihai Sürüm)

import asyncio
import tempfile
from pathlib import Path
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
import httpx

# Google Cloud Storage ile etkileşim için gerekli kütüphaneler
from google.cloud import storage
from google.cloud.exceptions import NotFound

from aiograpi import Client
from aiograpi.exceptions import LoginRequired

# GCS_BUCKET_NAME ayarını config'den çekiyoruz
from config import INSTA_USERNAME, INSTA_PASSWORD, PROXY_URL, GCS_BUCKET_NAME
from gmail_checker import get_instagram_code

# Yerel dosya yolu, geçici bir çalışma alanı olarak kullanılacak
SESSION_FILE_PATH = Path(tempfile.gettempdir()) / f"asuman_insta_session_{INSTA_USERNAME}.json"
# GCS'deki dosyanın adı ve yolu
SESSION_BLOB_NAME = f"sessions/{INSTA_USERNAME}.json"


def _upload_session_to_gcs(local_path: Path, destination_blob_name: str):
    """Lokaldeki oturum dosyasını Google Cloud Storage'a yükler."""
    if not GCS_BUCKET_NAME:
        logging.warning("⚠️ GCS_BUCKET_NAME ayarlanmamış, GCS'e yükleme atlanıyor.")
        return
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(str(local_path))
        logging.info(f"✅ Oturum başarıyla Google Cloud Storage'a yüklendi: gs://{GCS_BUCKET_NAME}/{destination_blob_name}")
    except Exception as e:
        logging.error(f"❌ HATA: Oturum GCS'e yüklenirken hata oluştu: {e}", exc_info=True)

def _download_session_from_gcs(source_blob_name: str, destination_local_path: Path):
    """Oturum dosyasını GCS'ten lokale indirir."""
    if not GCS_BUCKET_NAME:
        logging.warning("⚠️ GCS_BUCKET_NAME ayarlanmamış, GCS'ten indirme atlanıyor.")
        return
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(source_blob_name)
        
        logging.info(f"💾 Oturum GCS'ten indiriliyor: gs://{GCS_BUCKET_NAME}/{source_blob_name}")
        blob.download_to_filename(str(destination_local_path))
        logging.info(f"✅ Oturum başarıyla lokale indirildi: {destination_local_path}")
    except NotFound:
        logging.info("ℹ️ GCS'te oturum dosyası bulunamadı. İlk giriş yapılacak.")
    except Exception as e:
        logging.error(f"❌ HATA: Oturum GCS'ten indirilirken hata oluştu: {e}", exc_info=True)


class InstagramClientManager:
    """
    Instagram istemcisini yönetir, oturumu GCS üzerinden kalıcı hale getirir.
    """
    _client: Client = None

    async def get_client(self) -> Client:
        """
        Her zaman geçerli bir client nesnesi döndürmeyi garanti eder.
        Oturumu GCS'ten alır, kullanır ve güncel halini geri yükler.
        """
        if self._client:
            try:
                await self._client.get_timeline_feed(amount=1)
                logging.info("✅ Mevcut Instagram oturumu (hafızada) sağlıklı.")
                return self._client
            except Exception:
                logging.warning("⚠️ Hafızadaki oturumda sorun var. Yeniden oturum sağlanacak.")
                self._client = None

        try:
            logging.info(f"🚀 Yeni bir Instagram oturumu sağlanıyor...")
            
            _download_session_from_gcs(SESSION_BLOB_NAME, SESSION_FILE_PATH)
            
            new_client = Client()
            new_client.delay_range = [4, 11]

            if PROXY_URL:
                logging.info(f"🔌 Proxy için manuel httpx istemcisi oluşturuluyor: {PROXY_URL}")
                custom_httpx_client = httpx.AsyncClient(proxy=PROXY_URL)
                new_client.public._client = custom_httpx_client
                new_client.private._client = custom_httpx_client

            new_client.challenge_code_handler = self._challenge_code_handler

            if SESSION_FILE_PATH.exists():
                new_client.load_settings(SESSION_FILE_PATH)
                logging.info("🔑 Oturum dosyası belleğe yüklendi.")

            logging.info(f"🔒 '{INSTA_USERNAME}' olarak giriş yapılıyor (varsa oturum kullanılacak)...")
            await new_client.login(INSTA_USERNAME, INSTA_PASSWORD)
            logging.info("✅ Giriş başarılı. Oturum sağlandı.")

            new_client.dump_settings(SESSION_FILE_PATH)
            _upload_session_to_gcs(SESSION_FILE_PATH, SESSION_BLOB_NAME)

            self._client = new_client
            return self._client
            
        except Exception as e:
            logging.error(f"❌ KRİTİK HATA: Oturum sağlama sürecinde hata oluştu: {e}", exc_info=True)
            self._client = None
            raise

    async def _challenge_code_handler(self, username, choice):
        for i in range(12): 
            wait_time = random.uniform(15, 25)
            logging.info(f"Gmail kontrol ediliyor... ({i+1}/12). {int(wait_time)} saniye bekleniyor.")
            await asyncio.sleep(wait_time)
            code = get_instagram_code(for_username=username)
            if code:
                return code
        raise Exception("Gmail'den doğrulama kodu 3 dakika içinde alınamadı.")

insta_manager = InstagramClientManager()


class InstagramProcessor:
    """
    Instagram eylemlerini (mesaj kontrolü, gezinme) yürüten ve detaylı loglama yapan sınıf.
    """
    def __init__(self):
        self.own_user_id = None

    async def _get_client(self) -> Client:
        """Her işlemden önce geçerli bir client ve botun kendi ID'sini alır."""
        client = await insta_manager.get_client()
        if not self.own_user_id:
            self.own_user_id = str(client.user_id)
            logging.info(f"🤖 Botun kendi kullanıcı ID'si alındı: {self.own_user_id}")
        return client

    async def get_and_process_unread_messages(self) -> List[Dict[str, Any]]:
        cl = await self._get_client()
        yeni_mesajlar = []
        try:
            logging.info("📩 Mesajlar kontrol ediliyor...")
            threads = await cl.direct_threads(amount=20)
            logging.info(f"🔎 Toplam {len(threads)} adet konuşma başlığı bulundu.")

            if not threads:
                logging.info("📪 Gelen kutusu boş. İşlem tamamlandı.")
                return []

            for i, thread in enumerate(threads):
                logging.info(f"  [{i+1}/{len(threads)}] Konuşma ID inceleniyor: {thread.id} | Okunma durumu: {thread.read_state}")
                
                if not thread.messages:
                    logging.info(f"    -> Bu konuşma boş, atlanıyor.")
                    continue

                last_message = thread.messages[0]
                last_message_sender_id = str(last_message.user_id)

                if last_message_sender_id == self.own_user_id:
                    logging.info(f"    -> Son mesaj bot tarafından gönderilmiş, atlanıyor.")
                    continue

                if not thread.read_state:
                    if not last_message.text:
                        logging.warning(f"    -> YENİ MESAJ! Ancak içeriği boş veya medya. Atlanıyor.")
                        continue
                    
                    # --- HATA DÜZELTMESİ BURADA ---
                    # 'last_message.user' yerine, 'thread.users' listesinden doğru kullanıcıyı buluyoruz.
                    sender_username = "bilinmiyor"
                    for user in thread.users:
                        if str(user.pk) == last_message_sender_id:
                            sender_username = user.username
                            break
                    # --- HATA DÜZELTMESİ SONU ---

                    logging.info(f"    -> ✅ YENİ MESAJ BULUNDU! Kullanıcı: {sender_username}, İçerik: '{last_message.text[:50]}...'")
                    
                    message_data = {
                        "thread_id": thread.id,
                        "message_id": last_message.id,
                        "text": last_message.text,
                        "user_id": last_message_sender_id,
                        "username": sender_username
                    }
                    yeni_mesajlar.append(message_data)
                    logging.info(f"      -> Mesaj işlenmek üzere listeye eklendi. Konuşma görüldü olarak işaretleniyor.")
                    await cl.direct_send_seen(thread.id)
                else:
                    logging.info(f"    -> Bu konuşma zaten okunmuş olarak işaretli, atlanıyor.")

            if yeni_mesajlar:
                logging.info(f"✅ Toplam {len(yeni_mesajlar)} adet yeni mesaj işlenmek üzere Orkestra Şefi'ne gönderilecek.")
            else:
                logging.info("✅ Kontrol tamamlandı, işlenecek yeni mesaj bulunamadı.")
            
            return yeni_mesajlar
        except Exception as e:
            logging.error(f"❌ Mesaj işleme sırasında kritik bir hata oluştu: {e}", exc_info=True)
            return []

    async def deep_browse_session(self):
        # ... (Bu fonksiyon aynı kalabilir, loglaması zaten detaylı) ...
        cl = await self._get_client()
        duration_minutes = random.uniform(5, 15)
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        logging.info(f"🧠 Derin Gezinme Modu başladı. Süre: {int(duration_minutes)} dakika.")

        try:
            while datetime.now() < end_time:
                logging.info("    -> Ana sayfa akışı (timeline) kontrol ediliyor...")
                timeline_feed = await cl.feed_timeline(amount=random.randint(3, 7))
                if not timeline_feed:
                    await asyncio.sleep(30)
                    continue

                random_media = random.choice(timeline_feed)
                
                if random.random() < 0.15:
                    logging.info(f"      👍 '{random_media.user.username}' kullanıcısının gönderisi (PK: {random_media.pk}) beğeniliyor.")
                    await cl.media_like(random_media.pk)
                    await asyncio.sleep(random.uniform(5, 15))

                if random.random() < 0.30:
                    user_to_visit = random_media.user
                    logging.info(f"      👤 '{user_to_visit.username}' kullanıcısının profili ziyaret ediliyor...")
                    user_info = await cl.user_info_by_username(user_to_visit.username)
                    await asyncio.sleep(random.uniform(10, 20))
                    
                    logging.info(f"        -> '{user_to_visit.username}' kullanıcısının gönderilerine bakılıyor...")
                    user_medias = await cl.user_medias(user_info.pk, amount=random.randint(2, 5))
                    logging.info(f"        -> {len(user_medias)} adet gönderisine bakıldı.")
                    await asyncio.sleep(random.uniform(15, 30))

                logging.info("    -> Bir sonraki eylem için bekleniyor...")
                await asyncio.sleep(random.uniform(20, 60))
        except Exception as e:
            logging.error(f"❌ Derin gezinme sırasında hata: {e}", exc_info=True)
        finally:
            logging.info("🧠 Derin Gezinme Modu tamamlandı.")
