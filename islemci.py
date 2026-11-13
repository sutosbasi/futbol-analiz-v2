import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from supabase_client import get_supabase_client

load_dotenv()

def verileri_isle_ve_yukle():
    excel_dosya = "giris_basit.xlsx"
    if not os.path.exists(excel_dosya):
        print(f"[!] {excel_dosya} bulunamadı!")
        return False

    print(f"[+] '{excel_dosya}' okunuyor...")
    excel_sheets = pd.read_excel(excel_dosya, sheet_name=None, engine='openpyxl', skiprows=[1])
    
    sutun_esleme = {
        "Takım": "Squad", "Maç": "MP", "90s": "stats_Playing_Time_90s",
        "Gol": "Gls", "Asist": "Ast", "Poss": "Possession",
        "Sarı": "CrdY", "Kırmızı": "CrdR", "Şut": "Sh",
        "İsabetli": "SoT", "Penaltı": "PK", "Penaltı Den.": "PKatt",
        "Yediği Gol": "Keeper_GA"
    }

    df_list = []
    for sheet_adi, df_sheet in excel_sheets.items():
        if sheet_adi.upper() == "OKU" or len(df_sheet) == 0:
            continue
        df_sheet = df_sheet.rename(columns=sutun_esleme)
        df_sheet['Sezon'] = "2026-2027"
        df_sheet['Lig'] = sheet_adi
        df_list.append(df_sheet)

    if not df_list:
        print("[!] Excel'de işlenecek veri bulunamadı.")
        return False

    df = pd.concat(df_list, ignore_index=True)

    def bol(a, b):
        a = pd.to_numeric(a, errors='coerce').fillna(0).astype(float)
        b = pd.to_numeric(b, errors='coerce').fillna(0).astype(float)
        return (a / b.replace(0, pd.NA)).fillna(0)

    df['G+A'] = df['Gls'].fillna(0) + df['Ast'].fillna(0)
    df['SoT_pct'] = (bol(df['SoT'], df['Sh']) * 100).round(1)
    df['Sh_per90'] = bol(df['Sh'], df['stats_Playing_Time_90s']).round(2)
    df['SoT_per90'] = bol(df['SoT'], df['stats_Playing_Time_90s']).round(2)
    df['G_per_Sh'] = bol(df['Gls'], df['Sh']).round(2)
    df['G_per_SoT'] = bol(df['Gls'], df['SoT']).round(2)
    df['Keeper_GA90'] = bol(df['Keeper_GA'], df['MP']).round(2)

    df.columns = [col.lower() for col in df.columns]

    hedef_kolonlar = [
        'squad', 'sezon', 'lig', 'mp', 'stats_playing_time_90s', 
        'gls', 'ast', 'possession', 'crdy', 'crdr', 'sh', 'sot', 
        'pk', 'pkatt', 'keeper_ga', 'sot_pct', 'sh_per90', 
        'sot_per90', 'g_per_sh', 'g_per_sot', 'keeper_ga90'
    ]
    
    mevcut_kolonlar = [col for col in hedef_kolonlar if col in df.columns]
    df = df[mevcut_kolonlar]
    df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

    kayitlar = df.to_dict(orient="records")
    print(f"[+] Toplam {len(kayitlar)} takım verisi Supabase'e gönderiliyor...")

    supabase = get_supabase_client()
    batch_size = 500
    tablo_adi = "fb_takim_verileri"

    try:
        for i in range(0, len(kayitlar), batch_size):
            batch = kayitlar[i:i + batch_size]
            cleaned_batch = [{k: (v if pd.notnull(v) else None) for k, v in row.items()} for row in batch]
            supabase.table(tablo_adi).upsert(cleaned_batch, on_conflict="squad,sezon,lig").execute()
        print("[OK] İşlem Başarılı: Tüm veriler Supabase'e aktarıldı!")
        return True
    except Exception as e:
        print(f"[!] Supabase Hata: {e}")
        return False

if __name__ == "__main__":
    verileri_isle_ve_yukle()