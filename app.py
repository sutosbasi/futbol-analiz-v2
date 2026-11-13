import os
import pandas as pd
import unicodedata
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__)

# ============================================
# 1. SUPABASE BAĞLANTISI VE VERİ YÜKLEME
# ============================================
def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key: return None
    return create_client(url, key)

def verileri_yukle():
    supabase = get_supabase_client()
    if not supabase: return pd.DataFrame(), pd.DataFrame()
    try:
        # Genişletilmiş tüm lig ve sezon arşiv verilerini çekiyoruz
        resp_takim = supabase.table("fb_takim_verileri").select("*").execute()
        takimlar = pd.DataFrame(resp_takim.data) if resp_takim.data else pd.DataFrame()
        
        resp_mac = supabase.table("fb_maclar").select("*").execute()
        maclar = pd.DataFrame(resp_mac.data) if resp_mac.data else pd.DataFrame()
        
        if not maclar.empty:
            renames = {
                'tarih': 'Date',
                'ev': 'Home',
                'dep': 'Away',
                'ev_gol': 'HomeGoals',
                'dep_gol': 'AwayGoals',
                'sezon': 'Sezon',
                'lig': 'Lig'
            }
            maclar = maclar.rename(columns=renames)
            
        return takimlar, maclar
    except Exception as e:
        print(f"Veri yükleme hatası: {e}")
        return pd.DataFrame(), pd.DataFrame()

takimlar, maclar = verileri_yukle()

# ============================================
# 2. NORMALİZASYON VE LİSTELEME
# ============================================
ALIAS = {
    'tottenham hotspur': 'tottenham', 'manchester city': 'man city',
    'manchester united': 'man united', 'manchester utd': 'man united',
    'wolverhampton wanderers': 'wolves', 'wolverhampton': 'wolves',
    'brighton & hove albion': 'brighton', 'brighton and hove albion': 'brighton',
    'nottingham forest': 'nottm forest', "nott'm forest": 'nottm forest',
    'sheffield united': 'sheffield utd', 'west bromwich albion': 'west brom',
    'newcastle united': 'newcastle', 'leeds united': 'leeds',
    'west ham united': 'west ham', 'norwich city': 'norwich',
}

def normalize_takim(t):
    if pd.isna(t): return ''
    t = str(t).strip().lower()
    for tr, en in [('ı','i'),('İ','i'),('ş','s'),('ğ','g'),('ü','u'),('ö','o'),('ç','c')]:
        t = t.replace(tr, en)
    t = t.replace('istanbul basaksehir', 'basaksehir')
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    return ALIAS.get(t, t)

if not takimlar.empty:
    takimlar.columns = [c.lower() for c in takimlar.columns]
    if 'squad' in takimlar.columns:
        takimlar['_key_squad'] = takimlar['squad'].apply(normalize_takim)

if not maclar.empty:
    if 'Home' in maclar.columns: maclar['_key_home'] = maclar['Home'].apply(normalize_takim)
    if 'Away' in maclar.columns: maclar['_key_away'] = maclar['Away'].apply(normalize_takim)
    if 'Date' in maclar.columns: maclar['Date'] = pd.to_datetime(maclar['Date'], errors='coerce')

# Dinamik lig ve sezon eşlemeleri
LIG_TAKIMLARI = {}
if not takimlar.empty and 'lig' in takimlar.columns and 'squad' in takimlar.columns:
    for lig in sorted(takimlar['lig'].dropna().unique()):
        lt = takimlar[takimlar['lig'] == lig]
        LIG_TAKIMLARI[lig] = sorted(lt['squad'].unique().tolist())

# ============================================
# 3. İSTATİSTİK VE ANALİZ MOTORU
# ============================================
def guc_puani_hesapla(tv):
    mp = float(tv.get('mp', 1) or 1)
    if pd.isna(mp) or mp <= 0: mp = 1.0
    
    gls = float(tv.get('gls', 0) or 0)
    if pd.isna(gls): gls = 0.0
    
    ga = float(tv.get('keeper_ga', 0) or 0)
    if pd.isna(ga): ga = 0.0
    
    sot_pct = float(tv.get('sot_pct', 0) or 0)
    if pd.isna(sot_pct): sot_pct = 0.0
    
    poss = float(tv.get('poss', 50) or 50)
    if pd.isna(poss): poss = 50.0
    
    gls_pm = gls / mp
    ga_pm = ga / mp
    puan = 0
    puan += min(30, gls_pm * 12)
    puan += max(0, 20 - ga_pm * 8)
    puan += min(15, sot_pct / 5)
    puan += min(15, (poss - 40) / 2) if poss > 40 else 0
    return min(100, max(10, puan))

def takim_sezon_istatistikleri(takim_adi):
    t = takimlar[takimlar['squad'] == takim_adi]
    if t.empty: return None
    row = t.iloc[-1]
    
    mp = float(row.get('mp', 1) or 1)
    if pd.isna(mp) or mp <= 0: mp = 1.0
    
    gls = float(row.get('gls', 0) or 0)
    sh = float(row.get('sh', 0) or 0)
    sot = float(row.get('sot', 0) or 0)
    sot_pct = float(row.get('sot_pct', 0) or 0)
    poss = float(row.get('poss', 50) or 50)
    keeper_ga = float(row.get('keeper_ga', 0) or 0)
    
    return {
        'MP': int(mp), 'Gls': int(gls), 'Keeper_GA': int(keeper_ga),
        'Gls_pm': round(gls / mp, 2) if mp > 0 else 0,
        'Sh': int(sh), 'Sh_pm': round(sh / mp, 1) if mp > 0 else 0,
        'SoT': int(sot), 'SoT_pm': round(sot / mp, 1) if mp > 0 else 0,
        'SoT_pct': round(sot_pct, 1), 'Poss': round(poss, 1)
    }

def analiz_et(ev_adi, dep_adi, lig):
    if takimlar.empty: return None
    
    ev_row = takimlar[(takimlar['lig'] == lig) & (takimlar['squad'] == ev_adi)]
    dep_row = takimlar[(takimlar['lig'] == lig) & (takimlar['squad'] == dep_adi)]
    
    if ev_row.empty or dep_row.empty: return None
        
    t1 = ev_row.iloc[-1]
    t2 = dep_row.iloc[-1]
    
    ev_guc = guc_puani_hesapla(t1)
    dep_guc = guc_puani_hesapla(t2)
    
    t1_mp = max(float(t1.get('mp', 1) or 1), 1)
    t2_mp = max(float(t2.get('mp', 1) or 1), 1)
    
    ev_g_ort = float(t1.get('gls', 0) or 0) / t1_mp
    dep_g_ort = float(t2.get('gls', 0) or 0) / t2_mp
    toplam_beklenen_gol = ev_g_ort + dep_g_ort

    if ev_guc > dep_guc + 5:
        sonuc = f"{ev_adi} KAZANIR"
        guven = int(50 + (ev_guc - dep_guc))
    elif dep_guc > ev_guc + 5:
        sonuc = f"{dep_adi} KAZANIR"
        guven = int(50 + (dep_guc - ev_guc))
    else:
        sonuc = "BERABERLİK ADAYI"
        guven = 55

    return {
        'ev': ev_adi, 'dep': dep_adi, 'lig': lig,
        'ev_guc': round(ev_guc, 1), 'dep_guc': round(dep_guc, 1),
        'ev_sezon': takim_sezon_istatistikleri(ev_adi),
        'dep_sezon': takim_sezon_istatistikleri(dep_adi),
        'tahmin': {
            'sonuc': sonuc, 'guven': min(95, guven),
            'bek_gol': round(toplam_beklenen_gol, 2)
        }
    }

# ============================================
# 4. FLASK ROTALARI
# ============================================
@app.route("/", methods=["GET"])
def index():
    ligler = sorted(list(LIG_TAKIMLARI.keys()))
    sezonlar = sorted(takimlar['sezon'].dropna().unique().tolist()) if not takimlar.empty and 'sezon' in takimlar.columns else []
    return render_template("index.html", ligler=ligler, sezonlar=sezonlar)

@app.route("/api/takimlar/<lig>", methods=["GET"])
def api_takimlar(lig):
    takim_listesi = LIG_TAKIMLARI.get(lig, [])
    return jsonify({"takimlar": takim_listesi})

@app.route("/analiz", methods=["POST"])
def analiz_sayfasi():
    lig = request.form.get("lig")
    ev = request.form.get("ev")
    dep = request.form.get("dep")
    
    if not lig or not ev or not dep or ev == dep:
        return "<h1>Hata: Eksik veya aynı takımları seçtiniz.</h1><a href='/'>Geri Dön</a>"
        
    s = analiz_et(ev, dep, lig)
    if not s:
        return "<h1>Analiz verisi bulunamadı.</h1><a href='/'>Geri Dön</a>"
        
    return render_template("sonuc.html", s=s)

if __name__ == "__main__":
    app.run(debug=True)
