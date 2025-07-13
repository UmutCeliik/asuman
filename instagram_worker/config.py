# instagram-worker/config.py

import os
from google.cloud import secretmanager
import logging

# Sadece bir kez çalışması için basit bir kontrol
_secrets = {}

def get_secret(secret_id: str, version_id="latest") -> str:
    """Google Secret Manager'dan bir sır değerini çeker ve cache'ler."""
    if secret_id in _secrets:
        return _secrets[secret_id]

    project_id = os.getenv("GCP_PROJECT")
    if not project_id:
        logging.warning(f"GCP_PROJECT ortam değişkeni bulunamadı. Sır '{secret_id}' için .env dosyası deneniyor.")
        return os.getenv(secret_id.upper())

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        _secrets[secret_id] = secret_value
        return secret_value
    except Exception as e:
        logging.error(f"HATA: '{secret_id}' sırrı Secret Manager'dan okunamadı: {e}")
        # Yerel .env dosyasından okumayı dene
        return os.getenv(secret_id.upper())

# Ayarları Secret Manager'dan veya .env'den al
INSTA_USERNAME = get_secret("INSTA_USERNAME")
INSTA_PASSWORD = get_secret("INSTA_PASSWORD")
GMAIL_ADDRESS = get_secret("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = get_secret("GMAIL_APP_PASSWORD")
GMAIL_IMAP_SERVER = get_secret("GMAIL_IMAP_SERVER")
PROXY_URL = get_secret("PROXY_URL")
ORCHESTRATOR_SECRET_TOKEN = get_secret("ORCHESTRATOR_SECRET_TOKEN")
GCS_BUCKET_NAME = get_secret("GCS_BUCKET_NAME")
