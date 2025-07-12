# instagram-worker/worker_main.py (DÜZELTİLMİŞ HALİ)

from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
import asyncio
import logging

from instagram_client import InstagramProcessor
from security import verify_token

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global bir işlemci nesnesi oluşturuyoruz ama BAŞLATMIYORUZ.
processor = InstagramProcessor()

app = FastAPI(dependencies=[Depends(verify_token)])

# Lifespan fonksiyonuna artık ihtiyacımız yok, çünkü başlangıçta bir şey yapmıyoruz.

# Bu yardımcı fonksiyon, işlemcinin başlatıldığından emin olacak.
async def get_processor() -> InstagramProcessor:
    # Eğer istemci (cl) henüz başlatılmamışsa, şimdi başlat.
    if not processor.cl:
        logging.info("İşlemci ilk kez kullanılıyor, istemci başlatılıyor...")
        await processor.initialize_client()
    return processor

@app.get("/process-and-get-new-messages")
async def process_messages(processor: InstagramProcessor = Depends(get_processor)):
    try:
        new_messages = await processor.get_and_process_unread_messages()
        return {"status": "success", "new_messages": new_messages}
    except Exception as e:
        logging.error(f"Mesaj işleme sırasında kritik hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deep-browse-session")
async def start_deep_browse(processor: InstagramProcessor = Depends(get_processor)):
    try:
        # Bu işlemi arka planda çalıştır
        asyncio.create_task(processor.deep_browse_session())
        return {"status": "success", "detail": "Deep browse session started in the background."}
    except Exception as e:
        logging.error(f"Derin gezinme başlatılırken hata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", dependencies=None)
def health_check():
    # Bu endpoint, uygulamanın ayakta olduğunu anında doğrular.
    # Instagram'a bağlanmayı beklemez.
    return {"status": "ok"}