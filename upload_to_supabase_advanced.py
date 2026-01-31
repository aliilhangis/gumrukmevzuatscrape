import os
import requests
from supabase import create_client, Client
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Tuple, Dict, Optional
import logging

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase yapılandırması
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "gumruk-files")

# İşlem ayarları
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "10"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.environ.get("RETRY_DELAY", "2"))

# ============================================================================
# BURAYA LİNKLERİNİZİ EKLEYİN (virgül ile ayrılmış)
# ============================================================================
FILE_URLS = [
    "https://gumruk.com.tr/files/tutun_mamulleri_ve_alkollu_ickilerde_bandrol_denetimi_seri_no_01.htm",
    # Diğer linkleri buraya ekleyin, her satır virgül ile bitmeli:
    # "https://gumruk.com.tr/files/tutun_mamulleri_ve_alkollu_ickilerde_bandrol_denetimi_seri_no_02.htm",
    # "https://gumruk.com.tr/files/tutun_mamulleri_ve_alkollu_ickilerde_bandrol_denetimi_seri_no_03.htm",
]
# ============================================================================

# Supabase client oluştur
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_filename_from_url(url: str) -> str:
    """URL'den dosya adını çıkar"""
    return url.split('/')[-1]

def download_file(url: str, retry_count: int = 0) -> Tuple[str, Optional[bytes], Optional[str]]:
    """
    Belirtilen URL'deki dosyayı indir, gerekirse retry yap
    """
    file_name = get_filename_from_url(url)
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Dosya boyutunu kontrol et
        if len(response.content) == 0:
            raise Exception("Dosya boş")
        
        return (file_name, response.content, None)
    
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"İndirme hatası (deneme {retry_count + 1}/{MAX_RETRIES}): {file_name} - {str(e)}")
            time.sleep(RETRY_DELAY * (retry_count + 1))
            return download_file(url, retry_count + 1)
        else:
            return (file_name, None, f"Download failed after {MAX_RETRIES} retries: {str(e)}")

def upload_to_supabase(file_name: str, content: bytes, retry_count: int = 0) -> Tuple[str, bool, Optional[str]]:
    """
    Dosyayı Supabase bucket'a yükle, gerekirse retry yap
    """
    try:
        # Önce dosyanın var olup olmadığını kontrol et
        try:
            existing = supabase.storage.from_(BUCKET_NAME).list(path=file_name)
            file_exists = len(existing) > 0
        except:
            file_exists = False
        
        if file_exists:
            # Dosya varsa güncelle
            result = supabase.storage.from_(BUCKET_NAME).update(
                file=content,
                path=file_name,
                file_options={"content-type": "text/html; charset=windows-1254"}
            )
            logger.info(f"Dosya güncellendi: {file_name}")
        else:
            # Dosya yoksa yeni oluştur
            result = supabase.storage.from_(BUCKET_NAME).upload(
                file=content,
                path=file_name,
                file_options={"content-type": "text/html; charset=windows-1254"}
            )
            logger.info(f"Dosya yüklendi: {file_name}")
        
        return (file_name, True, None)
    
    except Exception as e:
        if retry_count < MAX_RETRIES:
            logger.warning(f"Yükleme hatası (deneme {retry_count + 1}/{MAX_RETRIES}): {file_name} - {str(e)}")
            time.sleep(RETRY_DELAY * (retry_count + 1))
            return upload_to_supabase(file_name, content, retry_count + 1)
        else:
            return (file_name, False, f"Upload failed after {MAX_RETRIES} retries: {str(e)}")

def process_file(url: str) -> Dict:
    """
    Dosyayı indir ve Supabase'e yükle
    """
    start_time = time.time()
    file_name = get_filename_from_url(url)
    
    # Dosyayı indir
    _, content, download_error = download_file(url)
    
    if download_error:
        return {
            "url": url,
            "file_name": file_name,
            "success": False,
            "error": download_error,
            "duration": time.time() - start_time
        }
    
    # Supabase'e yükle
    _, upload_success, upload_error = upload_to_supabase(file_name, content)
    
    if upload_error:
        return {
            "url": url,
            "file_name": file_name,
            "success": False,
            "error": upload_error,
            "duration": time.time() - start_time
        }
    
    return {
        "url": url,
        "file_name": file_name,
        "success": True,
        "error": None,
        "duration": time.time() - start_time,
        "size": len(content)
    }

def main():
    """
    Ana fonksiyon - dosyaları paralel olarak işle
    """
    # URL listesini temizle (boş satırları kaldır)
    clean_urls = [url.strip() for url in FILE_URLS if url.strip()]
    
    if not clean_urls:
        logger.error("HATA: Hiç URL bulunamadı! FILE_URLS listesine linkleri ekleyin.")
        exit(1)
    
    logger.info("="*60)
    logger.info("GUMRUK DOSYALARI SUPABASE YÜKLEME İŞLEMİ")
    logger.info("="*60)
    logger.info(f"Supabase URL: {SUPABASE_URL}")
    logger.info(f"Bucket: {BUCKET_NAME}")
    logger.info(f"Toplam dosya: {len(clean_urls)}")
    logger.info(f"Paralel işlem sayısı: {MAX_WORKERS}")
    logger.info(f"Maksimum retry: {MAX_RETRIES}")
    logger.info("="*60)
    
    # İstatistikler
    stats = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "total_size": 0,
        "total_duration": 0
    }
    
    failed_uploads = []
    start_time = time.time()
    
    # ThreadPoolExecutor ile paralel işlem
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Tüm URL'leri işleme kuyruğuna ekle
        future_to_url = {
            executor.submit(process_file, url): url 
            for url in clean_urls
        }
        
        # İşlemleri tamamlandıkça kontrol et
        for future in as_completed(future_to_url):
            result = future.result()
            stats["total"] += 1
            
            if result["success"]:
                stats["successful"] += 1
                stats["total_size"] += result.get("size", 0)
                stats["total_duration"] += result["duration"]
                logger.info(
                    f"[{stats['total']}/{len(clean_urls)}] ✓ {result['file_name']} "
                    f"({result.get('size', 0)/1024:.1f} KB, {result['duration']:.2f}s)"
                )
            else:
                stats["failed"] += 1
                failed_uploads.append(result)
                logger.error(
                    f"[{stats['total']}/{len(clean_urls)}] ✗ {result['file_name']}: "
                    f"{result['error']}"
                )
            
            # Her 100 dosyada bir özet göster
            if stats["total"] % 100 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / stats["total"]
                remaining = (len(clean_urls) - stats["total"]) * avg_time
                
                logger.info("")
                logger.info("--- İLERLEME ÖZETİ ---")
                logger.info(f"Tamamlanan: {stats['total']}/{len(clean_urls)}")
                logger.info(f"Başarılı: {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)")
                logger.info(f"Başarısız: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
                logger.info(f"Toplam boyut: {stats['total_size']/1024/1024:.2f} MB")
                logger.info(f"Geçen süre: {elapsed/60:.1f} dakika")
                logger.info(f"Tahmini kalan: {remaining/60:.1f} dakika")
                logger.info(f"Ortalama hız: {stats['successful']/(elapsed/60):.1f} dosya/dakika")
                logger.info("----------------------")
                logger.info("")
    
    # Sonuç özeti
    total_elapsed = time.time() - start_time
    logger.info("")
    logger.info("="*60)
    logger.info("İŞLEM TAMAMLANDI")
    logger.info("="*60)
    logger.info(f"Toplam dosya: {stats['total']}")
    logger.info(f"Başarılı yükleme: {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)")
    logger.info(f"Başarısız yükleme: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
    logger.info(f"Toplam boyut: {stats['total_size']/1024/1024:.2f} MB")
    logger.info(f"Toplam süre: {total_elapsed/60:.1f} dakika")
    logger.info(f"Ortalama hız: {stats['successful']/(total_elapsed/60):.1f} dosya/dakika")
    logger.info("="*60)
    
    if failed_uploads:
        logger.warning(f"\n{len(failed_uploads)} adet başarısız yükleme:")
        for failed in failed_uploads[:10]:  # İlk 10 hatayı göster
            logger.warning(f"  - {failed['file_name']}: {failed['error']}")
        
        if len(failed_uploads) > 10:
            logger.warning(f"  ... ve {len(failed_uploads) - 10} adet daha")
        
        # Başarısız dosyaları log dosyasına yaz
        with open("failed_uploads.log", "w", encoding="utf-8") as f:
            f.write("url,file_name,error\n")
            for failed in failed_uploads:
                f.write(f"{failed['url']},{failed['file_name']},\"{failed['error']}\"\n")
        logger.info("\nBaşarısız yüklemeler 'failed_uploads.log' dosyasına kaydedildi.")

if __name__ == "__main__":
    # Gerekli environment variable'ları kontrol et
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("HATA: SUPABASE_URL ve SUPABASE_KEY environment variable'ları ayarlanmalı!")
        exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\nİşlem kullanıcı tarafından durduruldu.")
        exit(0)
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {str(e)}", exc_info=True)
        exit(1)
