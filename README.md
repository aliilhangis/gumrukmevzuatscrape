# Gumruk Dosyalarını Supabase'e Yükleme

Bu proje, gumruk.com.tr sitesindeki 3268 adet HTML dosyasını Railway üzerinden Supabase bucket'ınıza yükler.

## Kurulum

### 1. Railway'de Proje Oluşturma

1. [Railway](https://railway.app/) hesabınıza giriş yapın
2. "New Project" → "Deploy from GitHub repo" seçin
3. Bu repository'yi seçin

### 2. Environment Variables Ayarlama

Railway dashboard'unuzda aşağıdaki environment variable'ları ekleyin:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
BUCKET_NAME=gumruk-files
```

**Önemli Notlar:**
- `SUPABASE_URL`: Supabase projenizin URL'si
- `SUPABASE_KEY`: Supabase anon key veya service role key
  - **Anon key**: Sadece public bucket'lar için
  - **Service role key**: Private bucket'lar ve bypass RLS için (önerilir)
- `BUCKET_NAME`: Dosyaların yükleneceği bucket adı (önceden oluşturulmuş olmalı)

### 3. Supabase Bucket Oluşturma

Supabase dashboard'unuzda:

1. Storage → "Create a new bucket"
2. Bucket adı: `gumruk-files` (veya tercih ettiğiniz ad)
3. Public/Private seçimi yapın
4. "Create bucket"

### 4. Deploy

Railway otomatik olarak projeyi deploy edecek ve script çalışmaya başlayacaktır.

## Özellikler

- ✅ Paralel yükleme (10 eşzamanlı dosya)
- ✅ Otomatik retry mekanizması
- ✅ İlerleme takibi
- ✅ Hata loglaması
- ✅ Dosya zaten varsa güncelleme
- ✅ Detaylı konsol çıktısı

## Dosya Formatı

Dosyalar şu formatta indirilir ve yüklenir:
```
tutun_mamulleri_ve_alkollu_ickilerde_bandrol_denetimi_seri_no_01.htm
tutun_mamulleri_ve_alkollu_ickilerde_bandrol_denetimi_seri_no_02.htm
...
tutun_mamulleri_ve_alkollu_ickilerde_bandrol_denetimi_seri_no_3268.htm
```

## Log Dosyaları

Başarısız yüklemeler `failed_uploads.log` dosyasına kaydedilir:
```
file_number,file_name,error_message
```

## Teknik Detaylar

- **Python**: 3.9+
- **Kütüphaneler**: 
  - `supabase`: Supabase Python SDK
  - `requests`: HTTP istekleri için
- **Encoding**: Windows-1254 (Türkçe karakterler için)
- **Content-Type**: text/html; charset=windows-1254

## Sorun Giderme

### "Authentication error" hatası
- `SUPABASE_KEY` değerini kontrol edin
- Service role key kullanmayı deneyin

### "Bucket not found" hatası
- Bucket adının doğru olduğundan emin olun
- Bucket'ın oluşturulduğunu kontrol edin

### "Rate limit" hatası
- Script'te `max_workers` değerini azaltın (örn: 5)
- `time.sleep()` ekleyerek istekler arasına gecikme ekleyin

## Lokal Test

Lokal olarak test etmek için:

```bash
# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Environment variable'ları ayarla
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"
export BUCKET_NAME="gumruk-files"

# Script'i çalıştır
python upload_to_supabase.py
```

## Lisans

MIT
