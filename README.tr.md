# RelAİ Workbench

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009485?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Electron](https://img.shields.io/badge/Electron-35-2F3246?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-6d8768.svg)](LICENSE)

**Kendi sunucunda çalışan, insan eli değmiş gibi görünen bir AI masası.**

RelAİ; sıcak, el yapımı bir web arayüzü ve Electron Windows istemcisi olan merkezi bir AI sunucusudur. Yerel [Ollama](https://ollama.com/) modellerini çalıştırır, gerçek bilgi gerektiren sorularda web'de arama yapar, dosyalarını okur; sohbetleri, kullanıcıları, rolleri ve yönetici istatistiklerini tek bir sakin yerde tutar.

> Belgeler: **Türkçe** · [English](README.md) · [Español](README.es.md)

---

## Neden öne çıkıyor?

- **Tahmin yerine gerçek.** Bilgi içeren sorular, model cevap vermeden önce DuckDuckGo HTML aramasından geçirilir. Saf matematik doğrudan hesaplanır.
- **Parmak izi olan bir arayüz.** Sıcak kağıt tonları, koyu "masa" kenar çubuğu, serif başlıklar, özel SVG ikonlar, monogram avatarlar ve gerçek bir aydınlık/karanlık anahtarı. Robot emoji yok, mor gradyan yok.
- **E-posta doğrulama.** Altı haneli kod, 10 dakika geçerlilik, 5 deneme hakkı, 60 saniyelik yeniden gönderme beklemesi ve doğrulamadan sonra otomatik giriş.
- **Tek kimlik, her yerde.** Kullanıcı adı *veya* e-posta ile giriş yapılır. Oturumlar, roller, yasaklı kullanıcılar, sohbet geçmişi ve dosya analizi web ile masaüstü arasında ortaktır.
- **Sesli giriş, sesli cevap.** Tarayıcı konuşma tanıma ile yazma, konuşma sentezi ile cevap dinleme.
- **İsteğe bağlı Discord yoldaşı.** Moderasyon, seviye, ekonomi, bilet, karşılama mesajları ve müzik modülleri dahil.

## Teknoloji yığını

| Katman | Teknoloji |
| --- | --- |
| API | FastAPI + Uvicorn |
| Depolama | SQLite (kullanıcılar, oturumlar, sohbetler, dosyalar, loglar) |
| Model | Ollama (yerel) |
| Web | Saf HTML / CSS / JavaScript — framework yok |
| Masaüstü | Electron 35 |
| E-posta | `smtp.json` üzerinden SMTP |

## Depo yapısı

```text
relai-workbench/
├── server/
│   ├── app.py            # API, sohbet hattı, zorunlu web arama
│   ├── auth.py           # PBKDF2 şifre + bearer oturum
│   ├── db.py             # SQLite şeması ve sorgular
│   ├── mailer.py         # SMTP doğrulama kodları
│   ├── ollama.py         # yerel model istemcisi
│   ├── tools.py          # web arama, hesap makinesi, hava durumu
│   ├── static/           # giriş, uygulama ve yönetici arayüzü
│   └── requirements.txt
├── desktop/              # Electron kabuğu (sunucu adresini yükler)
└── discord-bot/          # İsteğe bağlı Discord botu
```

## Hızlı başlangıç

### 1. Sunucuyu kur ve çalıştır

```bash
cd server
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Ortam değişkenlerini ayarla (PowerShell örneği):

```powershell
$env:OLLAMA_MODEL = 'gemma2:2b'
$env:ADMIN_USERNAME = 'admin'
$env:ADMIN_PASSWORD = 'guclu-bir-sifre-secin'
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

<http://localhost:8000> adresini aç. Yönetici paneli `/admin` yolunda.

### 2. Modeli indir

```bash
ollama pull gemma2:2b
```

`gemma2:2b`, 4 GB RAM'de hızlıdır. `qwen2.5:3b` daha güçlüdür ancak küçük makinelerde çok daha yavaştır.

### 3. Gerçek doğrulama e-postalarını etkinleştir

```bash
copy server\smtp.example.json server\smtp.json
```

`host`, `port`, `security`, `username`, `password` ve `from` alanlarını doldur. Gmail için hesap şifresi değil **uygulama şifresi** gerekir. SMTP ayarlanmazsa altı haneli kod kayıt ekranında gösterilir; akışı yine test edebilirsin.

### 4. Masaüstü istemcisini derle

```bash
cd desktop
npm install
copy config.example.json config.json
# "serverUrl" alanını sunucuna ayarla, örn. http://localhost:8000
npm run build
```

Kurulum dosyası `desktop/dist/` içinde oluşur. Electron penceresi web uygulamasını yüklediği için arayüz güncellemeleri yeniden derleme gerektirmez.

### 5. İsteğe bağlı Discord botu

```bash
cd discord-bot
copy config.example.json config.json
# bot token'ını config.json içine yapıştır
pip install -r requirements.txt
python bot.py
```

## API özeti

| Yöntem | Yol | Amaç |
| --- | --- | --- |
| POST | `/api/register` | Hesap oluştur + doğrulama kodu gönder |
| POST | `/api/verify-email` | Kodu kontrol et, oturum token'ı döndür |
| POST | `/api/resend-code` | Yeni kod iste (60 sn bekleme) |
| POST | `/api/login` | Kullanıcı adı veya e-posta ile giriş |
| GET | `/api/me` | Mevcut kullanıcı |
| POST | `/api/chat` | Asistana soru sor |
| GET / POST / DELETE | `/api/conversations`, `/api/files` | Geçmiş ve dosya analizi |
| GET | `/api/admin/stats`, `/api/admin/users` | Yönetici verileri |

## Güvenlik notları

- Varsayılan yönetici şifresini hemen değiştir.
- Herkese açmadan önce sunucunun önüne HTTPS koy (Caddy veya Nginx).
- `server/data/`, `server/smtp.json`, `desktop/config.json`, `discord-bot/config.json` ve herhangi bir `.env` dosyasını asla commit etme. `.gitignore` bunları zaten kapsıyor.

## Lisans

MIT — [LICENSE](LICENSE) dosyasına bak. Özenle yapıldı, şablondan değil.
