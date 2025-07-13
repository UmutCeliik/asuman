# instagram-worker/worker_main.py (JSON Loglama ile Nihai Sürüm)

import logging
from fastapi import FastAPI, HTTPException, Depends
import asyncio

# Yeni loglama yapılandırmamızı import ediyoruz.
# Bu, tüm logging.info, logging.error vb. çağrılarını JSON formatına dönüştürecek.
import logging_config as logging_config

from instagram_client import InstagramProcessor
from security import verify_token

# Artık global bir logger nesnesi kullanabiliriz.
logger = logging.getLogger(__name__)

processor = InstagramProcessor()
app = FastAPI(dependencies=[Depends(verify_token)])

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Instagram Worker uygulaması başlatılıyor.")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("🛑 Instagram Worker uygulaması kapatılıyor.")

async def get_processor() -> InstagramProcessor:
    """Dependency olarak kullanılacak ve global işlemci nesnesini döndürecek."""
    return processor

@app.get("/process-and-get-new-messages")
async def process_messages(proc: InstagramProcessor = Depends(get_processor)):
    """
    Instagram'daki yeni mesajları kontrol eder, işler ve Orkestra'ya geri döndürür.
    """
    try:
        new_messages = await proc.get_and_process_unread_messages()
        return {"status": "success", "new_messages": new_messages}
    except Exception as e:
        logger.error(f"Mesaj işleme endpoint'inde kritik hata.", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deep-browse-session")
async def start_deep_browse(proc: InstagramProcessor = Depends(get_processor)):
    """
    Botun insansı davranışlar sergilemesi için derin gezinme seansını başlatır.
    Bu işlem, isteği hemen yanıtlayıp arka planda devam eder.
    """
    try:
        asyncio.create_task(proc.deep_browse_session())
        return {"status": "success", "detail": "Deep browse session started in the background."}
    except Exception as e:
        logger.error(f"Derin gezinme başlatılırken hata.", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", dependencies=None)
def health_check():
    """
    Uygulamanın ayakta olup olmadığını kontrol etmek için basit bir sağlık kontrolü endpoint'i.
    """
    return {"status": "ok"}
