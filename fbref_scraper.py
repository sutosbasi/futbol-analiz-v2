import os
import time
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client
from playwright.sync_api import sync_playwright
import io

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase URL veya KEY bulunamadı!")
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

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
    if not supabase: return

    print("🚀 FBref Playwright Tarayıcı Botu Başlatıldı...")
    
    with sync_playwright() as p:
        # Gerçek bir tarayıcı açıyoruz (Headless modda, arayüzsüz)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for lig_adi, info in LIGLER.items():
            for sezon in SEZONLAR:
                print(f"📥 Çekiliyor: {lig_adi} - Sezon: {sezon}...")
                try:
                    url = f"https://fbref.com/en/comps/{info['comp_id']}/{sezon}/stats/{sezon}-{info['url_name']}-Stats"
                    
                    page.goto(url, timeout=60000)
                    page.wait_for_timeout(3000) # Sayfanın tam yüklenmesi için bekleme
                    
                    html_content = page.content()
                    
                    # Eğer Cloudflare sayfada kaldıysa kontrol et
                    if "Cloudflare" in html_content or "Access denied" in html_content:
                        print(f"⚠️ Cloudflare engeline takıldı ({lig_adi} - {sezon})")
                        continue

                    tables = pd.read_html(io.StringIO(html_content))
                    
                    if tables:
                        df = tables[0]
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.droplevel(0)
                        
                        df.columns = [c.lower() for c in df.columns]
                        
                        if 'squad' in df.columns:
                            count = 0
                            for _, row in df.iterrows():
                                takim_adi = row.get('squad')
                                if pd.isna(takim_adi) or "Squad" in str(takim_adi): continue
                                
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
                                
                                supabase.table("fb_takim_verileri").upsert(kayit, on_conflict="squad,lig,sezon").execute()
                                count += 1
                                
                            print(f"✅ Başarıyla Kaydedildi: {lig_adi} ({sezon}) - {count} takım işlendi.")
                    
                    time.sleep(4)
                    
                except Exception as e:
                    print(f"⚠️ Hata oluştu ({lig_adi} - {sezon}): {e}")
                    continue

        browser.close()

    print("🎉 Tüm veri çekme ve aktarım işlemleri tamamlandı!")

if __name__ == "__main__":
    fbref_veri_cek()
