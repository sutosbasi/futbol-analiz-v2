import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Supabase URL veya KEY bulunamadı! .env dosyanızı kontrol edin.")
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# FBref lig kodları ve ID'leri (Örnek majör ligler ve Süper Lig)
# İstediğiniz ligleri ve sezonları buraya ekleyebilir/çoğaltabilirsiniz.
LIGLER = {
    "Süper Lig": {"comp_id": "26", "url_name": "Turkish-Super-Lig"},
    "Premier League": {"comp_id": "9", "url_name": "Premier-League"},
    "La Liga": {"comp_id": "12", "url_name": "La-Liga"},
    "Serie A": {"comp_id": "11", "url_name": "Serie-A"},
    "Bundesliga": {"comp_id": "20", "url_name": "Bundesliga"},
    "Ligue 1": {"comp_id": "13", "url_name": "Ligue-1"}
}

SEZONLAR = ["2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"]

def fbref_veri_cek():
    supabase = get_supabase()
    if not supabase:
        return

    print("🚀 FBref Veri Çekme Botu Başlatıldı...")
    
    for lig_adi, info in LIGLER.items():
        for sezon in SEZONLAR:
            print(f"📥 Çekiliyor: {lig_adi} - Sezon: {sezon}...")
            try:
                # FBref standart lig istatistikleri URL yapısı
                # Not: Panda read_html doğrudan FBref tablolarını çekmek için en güçlü araçtır.
                url = f"https://fbref.com/en/sugs/comps/{info['comp_id']}/{sezon}/{sezon}-{info['url_name']}-Stats"
                
                # Alternatif URL formatı denemesi (Eğer slug uyuşmazlığı olursa pandas doğrudan url de kabul eder)
                # Standart tablo çekme:
                tables = pd.read_html(f"https://fbref.com/en/comps/{info['comp_id']}/{sezon}/stats/{sezon}-{info['url_name']}-Stats")
                
                if tables:
                    df = tables[0]
                    # Çok katmanlı sütun isimlerini düzleştir
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.droplevel(0)
                    
                    df.columns = [c.lower() for c in df.columns]
                    
                    if 'squad' in df.columns:
                        for _, row in df.iterrows():
                            takim_adi = row.get('squad')
                            if pd.isna(takim_adi): continue
                            
                            # Supabase'e gönderilecek veri sözlüğü
                            kayit = {
                                'squad': str(takim_adi).strip(),
                                'lig': lig_adi,
                                'sezon': sezon,
                                'mp': int(row.get('mp', 0)) if pd.notnull(row.get('mp')) else 0,
                                'gls': int(row.get('gls', 0)) if pd.notnull(row.get('gls')) else 0,
                                'sh': int(row.get('sh', 0)) if pd.notnull(row.get('sh')) else 0,
                                'sot': int(row.get('sot', 0)) if pd.notnull(row.get('sot')) else 0,
                                'sot_pct': float(row.get('sot%', 0)) if pd.notnull(row.get('sot%')) else 0.0,
                                'poss': float(row.get('poss', 50)) if pd.notnull(row.get('poss')) else 50.0,
                                'keeper_ga': int(row.get('ga', 0)) if pd.notnull(row.get('ga')) else 0
                            }
                            
                            # Supabase fb_takim_verileri tablosuna upsert et
                            # (Takım adı, lig ve sezona göre çakışmayı önlemek için upsert kullanılır)
                            supabase.table("fb_takim_verileri").upsert(kayit, on_conflict="squad,lig,sezon").execute()
                            
                print(f"✅ Başarıyla Kaydedildi: {lig_adi} ({sezon})")
                time.sleep(4) # FBref IP ban / rate limit yememek için bekleme süresi
                
            except Exception as e:
                print(f"⚠️ Hata oluştu ({lig_adi} - {sezon}): {e}")
                continue

    print("🎉 Tüm veri çekme ve aktarım işlemleri tamamlandı!")

if __name__ == "__main__":
    fbref_veri_cek()
