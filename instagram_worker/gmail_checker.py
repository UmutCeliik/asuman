# instagram-worker/gmail_checker.py

import imaplib
import email
from email.header import decode_header
import re
import logging
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GMAIL_IMAP_SERVER

def get_instagram_code(for_username: str) -> str | None:
    """
    Gmail'e bağlanır ve Instagram'dan gelen son doğrulama kodunu arar.
    Bu fonksiyon senkron çalışır.
    """
    logging.info(f"Gmail'de '{for_username}' için doğrulama kodu aranıyor...")

    try:
        # IMAP sunucusuna SSL ile bağlan ve giriş yap
        with imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER) as mail:
            mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            mail.select("inbox")
            
            # Instagram'dan gelen ve henüz görülmemiş e-postaları ara
            status, messages = mail.search(None, '(UNSEEN FROM "security@mail.instagram.com")')
            
            if status != "OK" or not messages[0]:
                logging.info("Yeni doğrulama e-postası bulunamadı.")
                return None

            # En son gelen e-postadan başlayarak kontrol et
            for email_id in reversed(messages[0].split()):
                _, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()

                        # E-posta içeriğinde kullanıcı adının ve 6 haneli kodun olup olmadığını kontrol et
                        if f"Hi {for_username}" in body or for_username in body:
                            code_match = re.search(r'\b(\d{6})\b', body)
                            if code_match:
                                code = code_match.group(1)
                                logging.info(f"Kod bulundu: {code}")
                                return code
        
        logging.warning("Uygun e-posta bulunamadı veya kod çıkarılamadı.")
        return None
    except Exception as e:
        logging.error(f"Gmail kontrolü sırasında hata: {e}")
        return None
