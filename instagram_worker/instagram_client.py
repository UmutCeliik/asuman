# instagram-worker/instagram_client.py

import asyncio
import tempfile
from pathlib import Path
import random
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

from aiograpi import Client
from aiograpi.exceptions import LoginRequired, ClientError
from aiograpi.types import UserShort

from config import INSTA_USERNAME, INSTA_PASSWORD, PROXY_URL
from gmail_checker import get_instagram_code

# Her kullanıcı için ayrı bir session dosyası oluştur
SESSION_FILE_PATH = Path(tempfile.gettempdir()) / f"asuman_insta_session_{INSTA_USERNAME}.json"

class InstagramSingleton:
    _instance = None
    cl: Client = None

    @classmethod
    async def get_instance(cls) -> Client:
        if cls._instance is None:
            logging.info("InstagramSingleton: Yeni bir örnek oluşturuluyor...")
            cls._instance = cls()
            await cls._instance.login_and_manage_session()
        
        try:
            await cls._instance.cl.get_timeline_feed(amount=1)
        except LoginRequired:
            logging.warning("Oturum geçersiz. Yeniden giriş yapılıyor...")
            await cls._instance.login_and_manage_session()
            
        return cls._instance.cl

    async def challenge_code_handler(self, username, choice):
        for i in range(12): 
            wait_time = random.uniform(15, 25)
            logging.info(f"Gmail kontrol ediliyor... ({i+1}/12). {int(wait_time)} saniye bekleniyor.")
            await asyncio.sleep(wait_time)
            code = get_instagram_code(for_username=username)
            if code:
                return code
        raise Exception("Gmail'den doğrulama kodu 3 dakika içinde alınamadı.")

    async def login_and_manage_session(self):
        self.cl = Client()
        self.cl.challenge_code_handler = self.challenge_code_handler
        self.cl.delay_range = [4, 11]
        logging.info(f"🤖 Anti-bot: İstekler arasına rastgele {self.cl.delay_range} sn bekleme eklendi.")

        if PROXY_URL:
            self.cl.set_proxy(PROXY_URL)

        try:
            if SESSION_FILE_PATH.exists():
                self.cl.load_settings(SESSION_FILE_PATH)

            await self.cl.login(INSTA_USERNAME, INSTA_PASSWORD)
            self.cl.dump_settings(SESSION_FILE_PATH)
            logging.info(f"'{INSTA_USERNAME}' olarak giriş yapıldı ve oturum kaydedildi.")
            await self.simulate_human_activity("login_warmup")
        except Exception as e:
            logging.error(f"Giriş sırasında beklenmedik bir hata oluştu: {e}", exc_info=True)
            raise

    async def simulate_human_activity(self, reason: str):
        logging.info(f"🤖 Anti-bot: İnsan aktivitesi simüle ediliyor ({reason})...")
        try:
            if random.random() < 0.75:
                await self.cl.feed_timeline(amount=random.randint(1, 2))
            if random.random() < 0.25:
                await self.cl.get_reels_tray_feed()
            logging.info("🤖 Anti-bot: Aktivite simülasyonu tamamlandı.")
        except Exception as e:
            logging.error(f"Aktivite simülasyonu sırasında hata: {e}")

class InstagramProcessor:
    def __init__(self):
        self.cl: Client = None

    async def initialize_client(self):
        if self.cl is None:
            self.cl = await InstagramSingleton.get_instance()

    async def send_message_humanized(self, user_id: str, text: str):
        await self.initialize_client()
        try:
            logging.info(f"✍️ '{user_id}' kullanıcısına mesaj gönderiliyor: '{text[:20]}...'")
            await self.cl.direct_send_typing_indicator(user_id)
            typing_delay = random.uniform(1, 4) + (len(text) / 20)
            await asyncio.sleep(typing_delay)
            await self.cl.direct_send(text, user_ids=[user_id])
            logging.info("✅ Mesaj başarıyla gönderildi.")
        except Exception as e:
            logging.error(f"Mesaj gönderilirken hata oluştu: {e}")

    async def deep_browse_session(self):
        await self.initialize_client()
        duration_minutes = random.uniform(5, 30)
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        logging.info(f"🧠 Derin Gezinme Modu başladı. Süre: {int(duration_minutes)} dakika.")

        try:
            while datetime.now() < end_time:
                timeline_feed = await self.cl.feed_timeline(amount=random.randint(3, 7))
                if not timeline_feed:
                    await asyncio.sleep(30)
                    continue

                random_media = random.choice(timeline_feed)
                
                if random.random() < 0.20:
                    logging.info(f"    👍 '{random_media.user.username}' kullanıcısının gönderisi beğeniliyor.")
                    await self.cl.media_like(random_media.pk)
                    await asyncio.sleep(random.uniform(5, 15))

                if random.random() < 0.40:
                    user_to_visit = random_media.user
                    logging.info(f"    👤 '{user_to_visit.username}' kullanıcısının profili ziyaret ediliyor...")
                    user_info = await self.cl.user_info_by_username(user_to_visit.username)
                    await asyncio.sleep(random.uniform(10, 20))
                    
                    user_medias = await self.cl.user_medias(user_info.pk, amount=random.randint(2, 5))
                    logging.info(f"    🖼️  {len(user_medias)} adet gönderisine bakıldı.")
                    await asyncio.sleep(random.uniform(15, 30))

                await asyncio.sleep(random.uniform(20, 60))
        except Exception as e:
            logging.error(f"Derin gezinme sırasında hata: {e}")
        finally:
            logging.info("🧠 Derin Gezinme Modu tamamlandı.")

    async def get_and_process_unread_messages(self) -> List[Dict[str, Any]]:
        await self.initialize_client()
        yeni_mesajlar = []
        try:
            threads = []
            if random.random() < 0.80:
                logging.info(">>> Verimli mod: Sadece okunmamış konuşmalar çekiliyor.")
                threads = await self.cl.direct_threads(selected_filter='unread', amount=10)
            else:
                logging.info(">>> İnsansı mod: Gelen kutusunun tamamı kontrol ediliyor.")
                threads = await self.cl.direct_threads(amount=20)

            if not threads:
                await self.simulate_human_activity("no_new_messages")
                return []

            for thread in threads:
                if thread.unread_count > 0 or not thread.read_state:
                    if not thread.messages or not thread.messages[0].text:
                        continue
                    
                    last_message = thread.messages[0]
                    message_data = {
                        "thread_id": thread.id,
                        "message_id": last_message.id,
                        "text": last_message.text,
                        "user_id": str(last_message.user_id),
                        "username": last_message.user.username if last_message.user else "bilinmiyor"
                    }
                    yeni_mesajlar.append(message_data)
                    await self.cl.direct_send_seen(thread.id)
            
            if yeni_mesajlar:
                logging.info(f"{len(yeni_mesajlar)} adet yeni mesaj işlenmek üzere bulundu.")
                await self.simulate_human_activity("after_processing_messages")
            
            return yeni_mesajlar
        except Exception as e:
            logging.error(f"Mesaj işleme sırasında bir hata oluştu: {e}")
            return []