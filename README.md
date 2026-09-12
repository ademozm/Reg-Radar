# PEG Radar

Peter Lynch'in sayısal checklist'ine (PEG oranı, kazanç büyümesi, borç,
kârlılık, kurumsal sahiplik) göre **ABD ve Türkiye (BIST)** hisselerini
tarayan bir Streamlit uygulaması.

**Bu sistem SADECE analiz yapar.** Hiçbir emir açmaz, hiçbir broker'a
bağlanmaz, hiçbir API anahtarı gerektirmez.

## Bu, eski `trading_system` projesinin yerini mi alıyor?

Evet. Önceki proje bir "tam otomatik trade sistemi" olarak başlamış,
sonra "sadece tarama" olarak yeniden tanımlanmıştı ama alttaki kod hâlâ
2500+ satırlık bir trade altyapısı (broker adapter'ları, risk motoru,
kill-switch, FastAPI, iki ayrı HTML/JS dashboard, Basic Auth) taşıyordu.
**PEG Radar bunların hiçbirini içermiyor** — sadece ~700 satır, tek
görevi olan (tarama) bir uygulama. Watchlist ve checklist eşikleri artık
`.env` dosyasını düzenleyip sunucuyu yeniden başlatmak yerine, doğrudan
uygulama arayüzünden değiştirilebiliyor.

Eski trade altyapısına hâlâ ihtiyacınız varsa, önceki sohbette paylaşılan
`trading_system.zip` bozulmadan duruyor.

## Kurulum

```bash
cd peg_radar
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env dosyasını isterseniz düzenleyin - varsayılanlarla da çalışır

streamlit run app.py
```

Tarayıcıda otomatik olarak `http://localhost:8501` açılır.

## Kullanım

1. Sol panelde ABD ve Türkiye izleme listelerini görürsünüz — istediğiniz
   gibi düzenleyebilirsiniz (virgülle ayrılmış, BIST hisseleri için `.IS`
   son eki gerekir, örn. `TCELL.IS`).
2. "Checklist eşikleri" ve "Yahoo Finance rate-limit ayarları" başlıklarını
   açarak PEG limiti, büyüme aralığı, borç limiti gibi parametreleri canlı
   olarak değiştirebilirsiniz — hiçbir dosya düzenlemeye veya yeniden
   başlatmaya gerek yok.
3. "Taramayı çalıştır" butonuna basın. İlerleme çubuğu hangi sembolün
   tarandığını gösterir. Aynı sembolü kısa süre içinde tekrar tararsanız
   (varsayılan: 1 saat içinde), yfinance'e tekrar gitmez, önbellekten
   döner — bu hem hızı artırır hem Yahoo'nun rate-limit'ini tetikleme
   riskini azaltır.
4. Ana tabloda piyasa/kategori filtresi, arama, sıralama var. Bir sembolü
   detay panelinden seçip PEG/PEGY, 52 haftalık aralık, analist hedef
   fiyatı, checklist'in madde madde dökümü gibi her şeyi görebilirsiniz.

## Otomatik tarama (her borsa kapanışında)

Uygulama, hafta içi her gün ilgili borsanın kapanışından kısa süre sonra
kendiliğinden tarar:

- **ABD**: varsayılan 16:15 (America/New_York, yani New York saatiyle -
  resmi kapanış 16:00, verinin güncellenmesi için 15 dakika payı var)
- **Türkiye/BIST**: varsayılan 18:10 (Europe/Istanbul - resmi kapanış 18:00)

Saatleri `.env`'den (`US_SCAN_HOUR`, `TR_SCAN_TIMEZONE` vb.) veya
uygulamayı hiç durdurmadan sol panelden açıp kapatabilirsiniz (panel
üzerinden sadece açık/kapalı değiştirilir, saatler için `.env`'i düzenleyip
yeniden başlatmak gerekir).

**Kritik mimari not:** Streamlit'in kendi başına bir zamanlayıcısı yoktur.
Otomatik tarama, uygulamanın çalıştığı Python süreci İÇİNDE arka planda
duran bir iş parçacığı (APScheduler) ile yapılıyor. Bu şu anlama gelir:

- Uygulama süreci **sürekli açık kalmalıdır** - bir sunucuda, VPS'te,
  Docker konteynerinde veya kendi bilgisayarınızda arka planda çalışıyor
  olmalı. Sadece bir tarayıcı sekmesi açıkken değil.
- **Streamlit Community Cloud gibi "kullanılmayınca uyuyan" platformlarda
  bu güvenilir çalışmaz** - uygulama uykudayken hiçbir kod çalışmaz.
  Günlük otomatik taramaya gerçekten güvenecekseniz, bunu 7/24 açık bir
  yerde (küçük bir VPS yeterli - Hetzner, DigitalOcean vb.) çalıştırın.
- Resmi piyasa tatilleri hesaba katılmıyor - sadece "hafta içi mi" diye
  bakılıyor. Tatil günü tarama yine tetiklenir, muhtemelen eski/hatalı
  veriyle karşılaşırsınız ama zararsızdır.

İzleme listesindeki "Kaydet (kalıcı)" butonuna basmadan yaptığınız
değişiklikler otomatik taramaya yansımaz - otomatik tarama her zaman
**kaydedilmiş** (veritabanındaki) listeyi kullanır.

### Borsa kapanışını beklemeden test etme

Sol panelde **"🧪 Otomatik taramayı borsa kapanışını beklemeden test et"**
başlığını açın. Buradaki butonlar cron zamanlayıcısının tetikleyeceği
**AYNI fonksiyonu** (`scheduled_us_scan` / `scheduled_tr_scan`) çağırır -
kaydedilmiş listeyi tarar, veritabanına yazar, Telegram kuruluysa bildirim
gönderir. Yani gerçek saatleri (16:15, 18:10) beklemeden tüm otomasyon
zincirinin uçtan uca çalıştığını hemen doğrulayabilirsiniz. Aynı panelde
sıradaki gerçek çalışma zamanlarını da (`Sıradaki ABD taraması: ...`)
görürsünüz - zamanlayıcının doğru saatlere kurulduğunu buradan teyit edin.

## İsteğe bağlı (manuel) tarama

Otomatik taramaya ek olarak, sol panelde her zaman "Taramayı şimdi
çalıştır" butonu vardır - kaydedilmiş olsun olmasın, o an kutularda yazan
listeyi hemen tarar. İki mod birbirini engellemez.

## Bildirimler (opsiyonel)

Otomatik tarama tamamlandığında bir özet (kaç hisse tarandı, kaç aday
bulundu, hangileri) loglanır. İsterseniz Telegram'a da göndertebilirsiniz:

1. Telegram'da @BotFather'a yazıp `/newbot` ile bir bot oluşturun, size
   verdiği token'ı `.env`'de `TELEGRAM_BOT_TOKEN`'a yapıştırın.
2. Botunuza Telegram'dan bir mesaj atın (herhangi bir şey yazın).
3. Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` adresine
   gidin, dönen JSON'da `"chat":{"id": ...}` kısmındaki sayıyı
   `TELEGRAM_CHAT_ID`'ye yapıştırın.
4. Uygulamayı yeniden başlatın (`.env` değişiklikleri için gerekli).
5. Sol paneldeki test bölümünde **"Sadece test bildirimi gönder"**
   butonuna basın - tarama yapmadan, sadece bağlantıyı doğrular. Birkaç
   saniye içinde Telegram'da bir mesaj görmelisiniz.

Bu alanlar boş bırakılırsa bildirim gönderilmez, sadece log'a yazılır -
bildirim kurmak zorunlu değildir.

## Şifre koruması (opsiyonel)

Varsayılan olarak şifre sorulmaz. Kendi bilgisayarınızda çalıştırıyorsanız
buna gerek yoktur. Uygulamayı Streamlit Community Cloud gibi genel bir
yere koyarsanız `.env`'de `APP_PASSWORD` set edin — basit bir şifre
kapısı devreye girer (çok kullanıcılı/güvenlik açısından kritik bir
senaryo için yeterli değildir, sadece rastgele ziyaretçileri engeller).

## Nerede çalıştırmalı? (barındırma seçenekleri)

Otomatik günlük taramanın gerçekten güvenilir olması için uygulama
sürecinin 7/24 açık kalması gerekiyor (yukarıdaki "Otomatik tarama"
bölümüne bakın). Hangi seçeneğin size uygun olduğu şuna bağlı:

| Seçenek | Günlük otomatik tarama için güvenilir mi? | Ücret | Ne zaman uygun |
|---|---|---|---|
| GitHub Codespaces | ❌ Hayır - hareketsizlikte uyur | Aylık ücretsiz kota var, sonra ücretli | Sadece geliştirme/test |
| Streamlit Community Cloud | ⚠️ Kısmen - trafik azsa uyuyabilir | Ücretsiz | Manuel taramaya bakmak için, günlük otomasyon için garanti değil |
| **Oracle Cloud Always Free** | ✅ Evet | **Kalıcı ücretsiz** (deneme değil) | Gerçekten her gün otomatik çalışsın, hiç ödeme yapmadan |
| Kiralık bir VPS (Hetzner, DigitalOcean vb.) | ✅ Evet | Ücretli (aylık ~$4-6) | Oracle'ın kayıt süreciyle uğraşmak istemiyorsanız |
| Kendi bilgisayarınız, sürekli açık | ✅ Evet (bilgisayar kapanmadığı sürece) | Ücretsiz (elektrik hariç) | VPS'e hiç gerek duymuyorsanız |

### Seçenek A (ücretsiz, önerilen): Oracle Cloud Always Free + Docker

Oracle Cloud'un "Always Free" katmanı, deneme süresi dolunca ücretlendirmeye
dönüşen diğer sağlayıcıların (AWS, GCP'nin çoğu kampanyası) aksine
**gerçekten kalıcı olarak ücretsiz** - süre sınırı yok. Yeterli güçte bir
ARM sunucu (4 çekirdek, 24 GB RAM'e kadar - bu proje için fazlasıyla yeterli)
veriyor. Dürüst olmak gerekirse: kayıt sırasında kredi kartı istiyor
(ücretlendirmek için değil, doğrulama için) ve bazı kullanıcılar kayıt/
doğrulama sürecinde zaman zaman sıkıntı yaşadığını bildiriyor - sabır
gerekebilir.

1. https://www.oracle.com/cloud/free/ adresinden hesap açın.
2. Console'da **Compute → Instances → Create Instance**.
3. Image olarak **Ubuntu** (22.04 veya 24.04), Shape olarak **"Ampere" (ARM, Always Free uygun)** seçin - "Always Free eligible" etiketli olanı seçtiğinizden emin olun, aksi halde ücretlendirilebilir.
4. SSH anahtarınızı ekleyin (Oracle otomatik oluşturabilir, indirin).
5. Instance oluşunca verilen genel (public) IP'ye SSH ile bağlanın:
   ```bash
   ssh -i indirdiğiniz-anahtar.key ubuntu@<INSTANCE_IP>
   ```
6. Sunucuda Docker'ı kurun:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # Bu komuttan sonra SSH oturumunu kapatıp tekrar açın (grup değişikliği için)
   ```
7. Projeyi çekin ve çalıştırın:
   ```bash
   git clone https://github.com/<kullanıcı-adınız>/<repo-adı>.git peg-radar
   cd peg-radar
   cp .env.example .env   # isterseniz düzenleyin (Telegram token'ları vb.)
   docker compose up -d --build
   ```
8. **Önemli:** Oracle'ın güvenlik duvarı (Security List) varsayılan olarak 8501 portunu kapalı tutar. Console'da instance'ınızın bağlı olduğu **VCN → Security Lists → Default Security List → Add Ingress Rule** ile TCP 8501 portunu açın (Source CIDR: `0.0.0.0/0`).
9. Tarayıcıda `http://<INSTANCE_IP>:8501` adresine gidin.

Bundan sonra bu sunucu 7/24 açık kalır, siz bilgisayarınızı kapatsanız
bile otomatik tarama çalışmaya devam eder - tam da istediğiniz şey bu.

**Alternatif (aynı şekilde kalıcı ücretsiz):** Google Cloud'un `e2-micro`
Always Free instance'ı (sadece belirli ABD bölgelerinde) - kurulum adımları
neredeyse birebir aynı, sadece Console arayüzü farklı.

### Seçenek B: Kiralık bir VPS (Docker ile, ücretli ama kayıt daha kolay)

Oracle'ın kayıt sürecinden kaçınmak isterseniz Hetzner veya DigitalOcean
gibi bir sağlayıcıdan aylık birkaç dolara bir sunucu kiralayabilirsiniz -
kurulum adımları yukarıdakiyle birebir aynı (Docker kur → `git clone` →
`docker compose up -d --build`), sadece 8. adımdaki güvenlik duvarı
ayarı sağlayıcıya göre değişir (genelde "Firewall" veya "Security Group"
bölümünden 8501 portunu açarsınız).

### Seçenek C: VPS'te Docker'sız (systemd ile)

Docker kullanmak istemiyorsanız `peg-radar.service` dosyasındaki
talimatları izleyin - aynı "sunucu yeniden başlasa bile otomatik kalkar"
garantisini systemd ile sağlar.

### Seçenek D: Streamlit Community Cloud (ücretsiz, ama günlük otomasyon garantisiz)

1. Bu klasörü bir GitHub reposuna yükleyin (private tutabilirsiniz).
2. https://share.streamlit.io adresinden GitHub hesabınızla giriş yapın.
3. "New app" → reponuzu seçin → main file olarak `app.py` gösterin → Deploy.
4. Ortam değişkenlerini "Advanced settings" kısmından girebilirsiniz.

Bunun bir faydası var: Streamlit Cloud'un IP aralığı GitHub Codespaces'ten
farklıdır - Codespaces'te rate-limit sorunu yaşıyorsanız burada
yaşamayabilirsiniz (garantili değil, denemeye değer). Ama Community Cloud
da hareketsiz kalan uygulamaları uyutabilir, bu yüzden "her gün saat
16:15'te kesin çalışsın" garantisi vermez - sadece manuel tarama için
bakmaya geldiğinizde açılsın istiyorsanız yeterlidir.

## Bilinen sorun: yfinance sürümüne göre yüzde alanlarının formatı değişebiliyor

`requirements.txt`'deki `yfinance>=0.2.50` çok esnek bir alt sınır - kendi
ortamınızda bu, geliştirirken test ettiğimizden çok daha yeni bir major
sürüme (örn. 1.x) kurulabiliyor. Bu sürümler arasında bazı alanların
formatı değişmiş görünüyor: temettü verimi ve kurumsal sahiplik oranı
bazı hisselerde **oran** (`0.03` = %3), bazılarında **zaten yüzde**
(`3.0` = %3) olarak geliyor. Bunu normalize etmeye çalışıyoruz
(`lynch_strategy.py`'de "1'den büyükse zaten yüzdedir" sezgisi) ama bu
tam kanıtlanmış bir kural değil, bir sezgisel varsayım - hâlâ tuhaf bir
değer görürseniz (örn. çok yüksek bir temettü verimi), o hisseyi kendi
kaynağınızdan (Yahoo Finance sitesi, şirketin yatırımcı ilişkileri
sayfası) çapraz kontrol edin.

## Bilinen sorun: Yahoo Finance rate-limit + bozuk crumb önbelleği

Yahoo Finance, art arda gelen istekleri bot koruması ile engelliyor
(429 Too Many Requests). Daha kötüsü: yfinance bu hatayı bazen geçerli
bir crumb (kimlik jetonu) sanıp diske kaydediyor, sonra her istekte bu
bozuk jetonu tekrar kullanıyor. Bu, yfinance'in resmi GitHub deposunda
(ranaroussi/yfinance, issue #2441, #2526) bilinen, güncel sürümde bile
devam eden bir hata.

Aldığımız önlemler:
- Semboller arasına bekleme (`LYNCH_REQUEST_DELAY_SECONDS`, varsayılan 4sn)
- Başarısız istekte üstel geri çekilmeli yeniden deneme (`LYNCH_MAX_RETRIES`)
- İlk başarısızlıkta yfinance'in bozuk çerez önbelleğini otomatik temizleme
- **st.cache_data ile 1 saatlik sonuç önbelleği** — bu, eski FastAPI
  sürümünde YOKTU ve sorunun büyük kısmının sebebiydi: her "taramayı
  çalıştır" tıklaması TÜM sembolleri sıfırdan çekiyordu

Hâlâ 429 alıyorsanız:
```bash
# Uygulamayı tamamen kapatın (Ctrl+C), sonra:
python scripts/reset_yfinance_cache.py
# Yeniden başlatın:
streamlit run app.py
```

Bu da işe yaramazsa, kullandığınız ağın (paylaşımlı bulut IP'si) Yahoo
tarafından geçici olarak engellenmiş olması ihtimali yüksek — biraz
bekleyin veya farklı bir ağdan/barındırmadan deneyin.

## CI (GitHub Actions)

`.github/workflows/ci.yml`, her push ve pull request'te otomatik çalışır,
iki aşamalı:

1. **`test` işi**: sözdizimi kontrolü → `ruff` ile lint (kullanılmayan
   import, tanımsız isim, eski Python sözdizimi vb.) → `pytest tests/ -v`
2. **`docker-smoke-test` işi**: (sadece `test` geçerse çalışır) Docker
   imajını build eder, konteyneri gerçekten başlatır, Streamlit'in sağlık
   endpoint'ine (`/_stcore/health`) 60 saniye içinde yanıt verip
   vermediğini kontrol eder. **Bu, benim bu geliştirme ortamında hiç
   test edemediğim `Dockerfile`'ı gerçekten doğrulayan tek mekanizma** -
   Docker kurulu olmadığı için imajı burada build edemedim, artık her
   push'ta CI bunu otomatik yapıyor.

GitHub'da repo → **Actions** sekmesinden çalıştığını görebilirsiniz.
README'nin en üstüne bir durum rozeti (badge) eklemek isterseniz:

```markdown
![CI](https://github.com/<kullanıcı-adınız>/<repo-adı>/actions/workflows/ci.yml/badge.svg)
```

Lint için ayrı bir `requirements-dev.txt` var (`ruff` içeriyor) -
uygulamayı çalıştırmak için buna ihtiyacınız yok, sadece CI ve isterseniz
kendi makinenizde `ruff check .` çalıştırmak için:

```bash
pip install -r requirements-dev.txt
ruff check .          # sorunları listeler
ruff check --fix .    # otomatik düzeltilebilenleri düzeltir
```

**Dürüst olmak gerekirse:** `ruff`'ı bu sandbox'ta da kuramadığım için
(ağ kapalı) gerçek bir lint taraması hiç çalıştıramadım - sadece basit
bir AST taramasıyla bariz "kullanılmayan import" durumlarını elle
kontrol ettim, temiz göründü. Ama ilk CI çalıştırmasında `ruff`'ın import
sıralaması gibi küçük, otomatik düzeltilebilir uyarılar bulması sürpriz
olmaz - böyle bir şey olursa `ruff check --fix .` çalıştırıp değişikliği
commit etmeniz yeterli.

## Test durumu

```bash
pytest tests/ -v
```

`tests/test_lynch_strategy.py` checklist mantığını (PEG hesaplama, eşik
kontrolleri, piyasa tespiti, yeniden deneme davranışı, yüzde alanı
normalizasyonu) sahte veriyle test ediyor. `tests/test_notifications.py`
bildirim özeti metninin doğru oluşturulduğunu, `tests/test_scheduler.py`
otomatik tarama orkestrasyonunun ("kapalıyken hiç taramamalı", "boş
listede hata vermemeli" gibi) davranışlarını test ediyor. Üçü de **ağ
kullanmadan**, mock'larla çalışır. **Bu sandbox'ta internet erişimi
kapalı olduğu için `pip install` yapılamadı, dolayısıyla testler burada
fiilen çalıştırılamadı** — sözdizimi kontrol edildi ve mantık elden
geçirildi, ama artık GitHub Actions CI'ınız her push'ta bunları gerçekten
çalıştırıp doğruluyor.

## Bilinçli olarak dışarıda bırakılanlar

- `_classify_category()` kaba bir sezgisel yaklaşım, gerçek Lynch
  kategorisini (döngüsel mi, hikaye hissesi mi) insan belirlemeli
- Checklist sadece NİCEL kriterleri kapsıyor; niteliksel değerlendirme
  (işi anlamak, hikayeyi doğrulamak) size ait
- Checklist eşikleri (PEG limiti vb.) sadece uygulama süreci ayaktayken
  geçerli - yeniden başlatınca `.env`'deki değerlere döner. Sadece
  izleme listesi kalıcı olarak kaydediliyor (veritabanında)
- Piyasa tatilleri hesaba katılmıyor - otomatik tarama sadece "hafta içi
  mi" diye bakıyor
- Otomatik tarama, uygulama sürecinin sürekli açık kalmasını gerektiriyor
  - bu, bu geliştirme ortamında (APScheduler kurulamadı, ağ kapalı) hiç
    test edilemedi; kendi ortamınızda mutlaka uçtan uca doğrulayın
- `Dockerfile`/`docker-compose.yml`/`peg-radar.service` bu ortamda Docker
  kurulu olmadığı için fiilen build/çalıştırılamadı - YAML sözdizimi
  doğrulandı, Dockerfile eski `trading_system` projesindekiyle aynı
  (orada sorunsuz çalışmıştı) desende yazıldı, ama ilk gerçek build'i
  kendi VPS'inizde yapmanız gerekiyor
- Çok kullanıcılı, güvenlik açısından kritik bir kimlik doğrulama yok
  (basit şifre kapısı yeterli değilse, kendi auth katmanınızı ekleyin)
