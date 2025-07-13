# Bu dosyayı hem Orkestra Şefi hem de İşçi projesine ekleyin.
# ortak/logging_config.py

import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Uygulama için yapılandırılmış JSON loglamasını ayarlar.
    Bu fonksiyon, her servisin ana dosyasının başında bir kez çağrılmalıdır.
    """
    # Mevcut tüm handler'ları temizle, böylece sadece bizimki kalır.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Yeni bir handler oluştur ve formatını JSON olarak ayarla.
    logHandler = logging.StreamHandler(sys.stdout)
    
    # Google Cloud Logging'in anlayacağı özel alanları ekliyoruz.
    # 'message' alanı ana metin olacak, 'severity' ise log seviyesini (INFO, ERROR vb.) gösterecek.
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        rename_fields={'levelname': 'severity'}
    )
    
    logHandler.setFormatter(formatter)
    
    # Root logger'ı ayarla.
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logHandler]
    )
    
    # Google Cloud kütüphanelerinin kendi loglarının seviyesini yükselterek
    # bizim loglarımızın arasında kaybolmalarını engelle.
    logging.getLogger('google.cloud').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return logging.getLogger(__name__)

# Hemen bir logger örneği oluştur.
logger = setup_logging()
