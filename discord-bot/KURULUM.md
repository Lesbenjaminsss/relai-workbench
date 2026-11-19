# Discord Bot Kurulum Kılavuzu

## 1. Discord'da bot oluşturun
1. https://discord.com/developers/applications adresine gidin.
2. **New Application** → isim verin → oluşturun.
3. Sol menüden **Bot** → **Add Bot**.
4. **Reset Token** ile token alın ve kopyalayın (kimseyle paylaşmayın).
5. Aşağıdaki intent'leri **açın**:
   - `Server Members Intent`
   - `Message Content Intent`
   - `Presence Intent` (opsiyonel)

## 2. Token'ı sunucuya girin
Sunucuda `C:\DiscordBot\config.json` dosyasını açın:

```json
{
  "token": "BURAYA_TOKEN_YAPISTIRIN",
  ...
}
```

Ardından `C:\DiscordBot\start_bot.bat` dosyasını yönetici olarak çalıştırın.

> `DiscordBot` adlı zamanlanmış görev sunucu açıldığında botu otomatik başlatır.

## 3. Botu sunucunuza davet edin
`client_id` değerini **OAuth2 → General → Application ID** bölümünden alın:

```
https://discord.com/oauth2/authorize?client_id=CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

`permissions=8` yönetici izni demektir (tüm özelliklerin çalışması için önerilir).

## 4. İsteğe bağlı ayarlar (config.json)

| Alan | Açıklama |
|---|---|
| `command_prefix` | Prefix komutlar için (varsayılan `!`) |
| `welcome_channel_id` | Karşılama mesajının gönderileceği kanal ID |
| `welcome_role_id` | Katılan üyeye otomatik verilecek rol ID |
| `log_channel_id` | Moderasyon/log mesajlarının gideceği kanal ID |
| `ticket_category_id` | Ticket kanallarının açılacağı kategori ID |
| `ai_api_key` | OpenAI API anahtarı (`ask` komutu için) |
| `ai_model` | Varsayılan `gpt-4o-mini` |
| `level_role_rewards` | Seviye → rol ID eşlemesi |
| `automod.banned_words` | Yasaklı kelime listesi |

## 5. Komutlar
Bot içinde `/help` yazın (veya `!help`). Slash komutlar ilk açılışta 1 dakika içinde senkronize olur.

## 6. Özellik listesi
- **Moderasyon:** ban, kick, mute, warn, clear, slowmode, lock/unlock + AutoMod (link, davet, kelime, spam, etiket)
- **Karşılama:** hoş geldin mesajı, otomatik rol, reaksiyon rolleri, rol menüsü
- **Seviye:** XP, level, sıralama, seviye rol ödülleri
- **Ekonomi:** günlük ödül, çalışma, transfer, mağaza, zenginler listesi
- **Ticket:** butonla ticket açma, transcript kaydı, kapatma
- **Müzik:** çal, kuyruk, atla, ses, duraklat (FFmpeg kurulu)
- **Log:** mesaj silme/düzenleme, katılım/ayrılma, rol, kanal değişiklikleri
- **Eğlence:** anket, çekiliş, zar, yazı-tura, 8ball
- **AI:** OpenAI destekli soru-cevap ve AI sohbet kanalları

## 7. Sorun giderme
- Bot çevrimdışıysa: `C:\DiscordBot\start_bot.bat` çalıştırın, konsoldaki hatayı okuyun.
- Slash komutlar görünmüyorsa: botu yeniden başlatın (sync açılışta yapılır).
- Müzik çalışmıyorsa: `C:\DiscordBot\ffmpeg\ffmpeg.exe` var mı kontrol edin.
