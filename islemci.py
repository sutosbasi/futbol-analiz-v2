import os
import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase_client import get_supabase_client

load_dotenv()

def verileri_isle_ve_yukle():
    print("[+] FBref'ten cloudscraper ile gerçek veriler kazınıyor...")
    
    # Cloudflare engellerini aşmak için özel scraper oluşturuyoruz
    scraper = cloudscraper.create_scraper()
    
    # Örnek olarak Premier League FBref istatistik sayfası
    url = "https://fbref.com/en/comps/9/Premier-League-Stats"
    
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"[!] FBref sayfasına erişilemedi. HTTP Kodu: {response.status_code}")
            return False
            
        # Sayfadaki tüm tabloları pandas ile çekelim
        tables = pd.read_html(response.text, match="Regular season")
        if not tables:
            # Alternatif tablo arama
            tables = pd.read_html(response.text)
            
        if not tables:
            print("[!] Sayfada uygun tablo bulunamadı.")
            return False
            
        df = tables[0]
        
        # Çok katmanlı sütun isimlerini düzeltme (MultiIndex kontrolü)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(0)
            
        print(f"[+] Başarıyla {len(df)} satır gerçek veri çekildi. Supabase'e işleniyor...")
        
        # Sütun eşleme ve Supabase formatına hazırlama
        # (FBref sütun adlarını veritabanı şemanızla eşleştiriyoruz)
        kayitlar = []
        for _, row in df.iterrows():
            squad_name = str(row.get("Squad", row.get("Takım", "Bilinmeyen")))
            if squad_name == "nan" or not squad_name:
                continue
                
            kayitlar.append({
                "squad": squad_name,
                "sezon": "2025-2026",
                "lig": "ENG-Premier League",
                "mp": int(row.get("MP", 0)) if pd.notnull(row.get("MP")) else 0,
                "gls": int(row.get("Gls", 0)) if pd.notnull(row.get("Gls")) else 0,
                "ast": int(row.get("Ast", 0)) if pd.notnull(row.get("Ast")) else 0,
                "possession": float(row.get("Poss", 50.0)) if pd.notnull(row.get("Poss")) else 50.0,
                "sh": int(row.get("Sh", 0)) if pd.notnull(row.get("Sh")) else 0,
                "sot": int(row.get("SoT", 0)) if pd.notnull(row.get("SoT")) else 0,
            })
            
        if not kayitlar:
            print("[!] İşlenecek geçerli kayıt bulunamadı.")
            return False

        supabase = get_supabase_client()
        tablo_adi = "fb_takim_verileri"
        
        # Supabase'e upsert et
        for item in kayitlar:
            supabase.table(tablo_adi).upsert(item, on_conflict="squad,sezon,lig").execute()

        print("[OK] Gerçek FBref verileri Supabase'e başarıyla aktarıldı!")
        return True

    except Exception as e:
        print(f"[!] FBref Kazıma Hatası: {e}")
        return False

if __name__ == "__main__":
    verileri_isle_ve_yukle()