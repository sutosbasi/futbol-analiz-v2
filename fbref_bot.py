import os
import time
import pandas as pd
import numpy as np
import requests
from io import StringIO
from dotenv import load_dotenv
from supabase_client import get_supabase_client

load_dotenv()

LIGLER = {
    "ENG-Premier League": "9/Premier-League-Stats",
    "ESP-La Liga": "12/La-Liga-Stats",
    "ITA-Serie A": "11/Serie-A-Stats",
    "GER-Bundesliga": "20/Bundesliga-Stats",
    "FRA-Ligue 1": "13/Ligue-1-Stats",
    "TUR-Süper Lig": "26/Super-Lig-Stats"
}

SEZONLER = [2020, 2021, 2022, 2023, 2024, 2025]

def fbref_verilerini_cek_ve_yukle():
    print("=" * 60)
    print("FBREF BYPASS SCRAPER VE SUPABASE AKTARIMI BAŞLATILDI")
    print("=" * 60)

    supabase = get_supabase_client()
    tablo_adi = "fb_takim_verileri"
    toplam_basarili = 0

    # Gerçek Tarayıcı Headers (403 Engeline Karşı)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
        "Referer": "https://fbref.com/"
    }

    for lig_adi, lig_path in LIGLER.items():
        for yil in SEZONLER:
            sezon_str = f"{yil}-{yil+1}"
            url = f"https://fbref.com/en/squads/{yil}/{lig_path}"
            
            try:
                print(f"[+] Çekiliyor: {lig_adi} | Sezon: {sezon_str}")
                
                # İstekte 403 hatasını aşmak için requests ile HTML'i çekip pandas'a veriyoruz
                response = requests.get(url, headers=headers)
                if response.status_code != 200:
                    print(f"    [!] HTTP Durum Kodu: {response.status_code} (Engellendi)")
                    continue
                
                dfs = pd.read_html(StringIO(response.text))
                if not dfs:
                    print(f"    [!] Sayfada tablo bulunamadı.")
                    continue
                
                df = dfs[0]
                
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join(col).strip() for col in df.columns.values]
                
                df = df.reset_index()
                
                renames = {}
                for col in df.columns:
                    c_lower = col.lower()
                    if 'squad' in c_lower or 'team' in c_lower:
                        renames[col] = 'squad'
                    elif 'mp' in c_lower or 'played' in c_lower:
                        renames[col] = 'mp'
                    elif 'gls' in c_lower or 'goals' in c_lower:
                        if 'against' not in c_lower and 'ga' not in c_lower:
                            renames[col] = 'gls'
                    elif 'ast' in c_lower:
                        renames[col] = 'ast'
                    elif 'poss' in c_lower:
                        renames[col] = 'possession'

                df = df.rename(columns=renames)
                
                if 'squad' not in df.columns:
                    continue

                df['sezon'] = sezon_str
                df['lig'] = lig_adi

                for col in ['mp', 'gls', 'ast', 'possession', 'sh', 'sot', 'pk', 'pkatt', 'keeper_ga']:
                    if col not in df.columns:
                        df[col] = 0
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                df.columns = [c.lower() for c in df.columns]
                df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

                kayitlar = df.to_dict(orient="records")
                
                batch_size = 500
                for i in range(0, len(kayitlar), batch_size):
                    batch = kayitlar[i:i + batch_size]
                    supabase.table(tablo_adi).upsert(batch, on_conflict="squad,sezon,lig").execute()

                print(f"    [OK] {len(kayitlar)} takım kaydı başarıyla yüklendi.")
                toplam_basarili += len(kayitlar)
                
                # Sunucuyu boğmamak ve ban yememek için bekleme
                time.sleep(4)

            except Exception as e:
                print(f"    [!] Hata ({lig_adi} - {sezon_str}): {e}")
                continue

    print("\n" + "=" * 60)
    print(f"[TAMAMLANDI] Toplam {toplam_basarili} kayıt Supabase'e aktarıldı!")
    print("=" * 60)

if __name__ == "__main__":
    fbref_verilerini_cek_ve_yukle()