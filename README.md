# Ultra-İnsansı Instagram Mesaj İşleme Botu

Bu proje, Instagram'dan gelen direkt mesajları otomatik olarak işlemek ve bu işlemi yaparken bot tespit sistemlerine yakalanmamak için gelişmiş "insansı" davranışlar sergilemek üzere tasarlanmıştır.

## Mimarinin Bileşenleri

Sistem, iki ana Google Cloud Platform (GCP) hizmeti üzerine kuruludur:

1.  **İşçi Servisi (Cloud Run):**
    * `aiograpi` kütüphanesini kullanarak Instagram ile tüm iletişimi kurar.
    * Giriş yapar, oturumu yönetir, proxy kullanır.
    * Mesajları çeker, okundu olarak işaretler.
    * "Derin gezinme" (ana sayfada dolaşma, profil ziyaret etme, gönderi beğenme) gibi insansı davranışları sergiler.
    * FastAPI ile oluşturulmuş bir web servisidir ve sürekli çalışır.

2.  **Orkestra Şefi (Cloud Function):**
    * Her 15 dakikada bir Cloud Scheduler tarafından tetiklenir.
    * Botun uyku/uyanma durumunu Firestore üzerinden kontrol eder.
    * Günün saatine ve rastgele bir seçime göre İşçi Servisi'ne hangi eylemi yapacağını (mesaj kontrolü mü, derin gezinme mi) söyler.
    * Botun gece uyumasını ve sabah uyanmasını sağlar.

## Kurulum ve Deployment Adımları

### Ön Gereksinimler

1.  Bir Google Cloud Projesi.
2.  `gcloud` CLI'nin bilgisayarınızda kurulu ve ayarlı olması.
3.  Projenizde **Cloud Run, Cloud Functions, Cloud Scheduler, Firestore, ve Secret Manager** API'lerinin aktif edilmiş olması.
4.  Instagram hesabınız için bir adet konut/mobil **Proxy URL**'si.

### Adım 1: Gizli Bilgilerin (Secrets) Ayarlanması

GCP Secret Manager'a giderek aşağıdaki sırları oluşturun:

* `INSTA_USERNAME`: Instagram kullanıcı adınız.
* `INSTA_PASSWORD`: Instagram şifreniz.
* `PROXY_URL`: Proxy adresiniz (örn: `http://user:pass@host:port`).
* `GMAIL_ADDRESS`: Doğrulama kodları için kullanılacak Gmail adresi.
* `GMAIL_APP_PASSWORD`: Gmail için oluşturulmuş uygulama şifresi.
* `GMAIL_IMAP_SERVER`: Gmail IMAP sunucusu (örn: `imap.gmail.com`).
* `ORCHESTRATOR_SECRET_TOKEN`: Orkestra Şefi ile İşçi arasındaki iletişimi güvence altına almak için rastgele oluşturulmuş bir şifre (örn: `my-super-secret-string-123`).

### Adım 2: İşçi Servisi'nin (Cloud Run) Deploy Edilmesi

1.  Terminalde `instagram-worker` klasörüne gidin.
2.  Aşağıdaki komut ile servisi derleyip Cloud Run'a yükleyin:

    ```bash
    gcloud run deploy instagram-worker-service \
      --source . \
      --platform managed \
      --region europe-west1 \
      --allow-unauthenticated \
      --timeout=540s \
      --memory=512Mi
    ```
3.  Deployment tamamlandığında size bir **Servis URL**'i verilecektir. Bu URL'yi bir yere not edin.

### Adım 3: Orkestra Şefi'nin (Cloud Function) Deploy Edilmesi

1.  `cloud-function-orchestrator/main.py` dosyasındaki `INSTA_WORKER_URL` değişkenini, bir önceki adımda aldığınız Servis URL'i ile güncelleyin.
2.  Terminalde `cloud-function-orchestrator` klasörüne gidin.
3.  Aşağıdaki komut ile fonksiyonu deploy edin:

    ```bash
    gcloud functions deploy orchestrate-bot-activity \
      --gen2 \
      --runtime=python311 \
      --region=europe-west1 \
      --source=. \
      --entry-point=orchestrate_bot_activity \
      --trigger-topic=firebase.schedule.orchestrate-bot-activity.v1 \
      --timeout=540s \
      --memory=512Mi
    ```
4.  Cloud Scheduler'a giderek `firebase-schedule-orchestrate-bot-activity-v1` isimli görevin "frequency" (sıklık) ayarını `every 15 minutes` olarak kontrol edin.

Sistem artık canlı! Firestore'daki `bot_system_state` koleksiyonunu ve servislerin loglarını takip ederek botun aktivitelerini izleyebilirsiniz.
